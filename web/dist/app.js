const element = id => document.getElementById(id);
const source = element('source');
const canvas = element('canvas');
const context = canvas.getContext('2d');
const file = element('file');
const settings = element('settings');
const scrub = element('scrub');
const output = element('result-video');
const progress = element('progress');
const cancel = element('cancel');
const ratios = {'4:5': [720,900], '9:16': [720,1280], '1:1': [720,720], '16:9': [1280,720]};
let inputUrl, outputUrl, audio, audioDestination, stopExport;
let speechWorker, decodedAudio, captionWords = [], captionKey = '', generationId = 0;
let accent = '#95dfcb';
const status = message => { element('status').textContent = message; };

function currentCaptionKey() {
  return [element('start').valueAsNumber, element('end').valueAsNumber, element('language').value].join('/');
}

function wordsAtTime() {
  if (element('caption-mode').value === 'none') return null;
  if (element('caption-mode').value !== 'auto' || !captionWords.length || captionKey !== currentCaptionKey()) return null;
  const current = captionWords.findIndex(word => source.currentTime >= word.start && source.currentTime < word.end);
  if (current < 0) return [];
  const offset = Math.floor(current / 3) * 3;
  return captionWords.slice(offset, offset + 3).map((word, index) => ({
    text: word.text,
    active: index + offset === current,
  }));
}

function draw() {
  if (source.readyState < 2) return;
  const {width, height} = canvas;
  const studio = element('layout').value === 'studio';
  const scale = Math.min(width * (studio ? .92 : 1) / source.videoWidth,
    height * (studio ? .72 : 1) / source.videoHeight);
  const w = source.videoWidth * scale;
  const h = source.videoHeight * scale;
  const y = height * (studio ? .42 : .5) - h / 2;
  context.fillStyle = '#111923';
  context.fillRect(0, 0, width, height);
  context.drawImage(source, (width - w) / 2, y, w, h);
  if (element('caption-mode').value === 'none') return;
  const timed = wordsAtTime();
  if (timed && !timed.length) return;
  const caption = timed ? timed.map(word => word.text).join(' ') : element('caption').value.trim();
  if (!caption) return;
  const size = Math.round(width * .043);
  context.font = '700 ' + size + 'px "' + element('font').value + '", sans-serif';
  context.textAlign = 'center';
  context.textBaseline = 'middle';
  const lines = [''];
  for (const word of caption.split(/\s+/)) {
    const i = lines.length - 1;
    const next = lines[i] ? lines[i] + ' ' + word : word;
    if (lines[i] && context.measureText(next).width > width * .84) lines.push(word);
    else lines[i] = next;
  }
  const lineHeight = size * 1.2;
  const center = studio ? Math.min(height * .89, y + h + height * .08) : height * .84;
  if (timed) {
    const space = context.measureText(' ').width;
    const widths = timed.map(word => context.measureText(word.text).width);
    const totalWidth = widths.reduce((sum, value) => sum + value, 0) + space * (timed.length - 1);
    const scaleText = Math.min(1, width * .86 / totalWidth);
    context.save();
    context.translate(width / 2, center);
    context.scale(scaleText, scaleText);
    context.textAlign = 'left';
    context.lineWidth = 5;
    context.strokeStyle = '#111923';
    let x = -totalWidth / 2;
    timed.forEach((word, index) => {
      context.strokeText(word.text, x, 0);
      context.fillStyle = word.active ? accent : '#fff8ed';
      context.fillText(word.text, x, 0);
      x += widths[index] + space;
    });
    context.restore();
    return;
  }
  lines.forEach((line, i) => {
    const ty = center + (i - (lines.length - 1) / 2) * lineHeight;
    context.lineWidth = 5;
    context.strokeStyle = '#111923';
    context.strokeText(line, width / 2, ty, width * .86);
    context.fillStyle = '#fff8ed';
    context.fillText(line, width / 2, ty, width * .86);
  });
}

function resize() {
  const ratio = element('ratio').value;
  const [width,height] = ratios[ratio];
  canvas.width = width;
  canvas.height = height;
  element('dimensions').textContent = ratio + ' · ' + width + ' × ' + height;
  draw();
}
function updateTime() {
  scrub.value = source.currentTime;
  const minutes = Math.floor(source.currentTime / 60);
  const seconds = (source.currentTime % 60).toFixed(1).padStart(4, '0');
  element('time').textContent = minutes + ':' + seconds;
}
function clearResult() {
  element('result').hidden = true;
  output.removeAttribute('src');
  output.load();
  element('save').removeAttribute('href');
  if (outputUrl) URL.revokeObjectURL(outputUrl);
  outputUrl = null;
}
file.addEventListener('change', () => {
  const chosen = file.files[0];
  if (!chosen) return;
  captionWords = [];
  captionKey = '';
  decodedAudio = undefined;
  element('caption').value = '';
  clearResult();
  settings.disabled = true;
  scrub.disabled = true;
  canvas.hidden = true;
  element('empty').hidden = false;
  element('file-name').textContent = chosen.name;
  if (inputUrl) URL.revokeObjectURL(inputUrl);
  inputUrl = URL.createObjectURL(chosen);
  source.src = inputUrl;
  status('Reading video…');
});
source.addEventListener('loadeddata', () => {
  if (!Number.isFinite(source.duration) || !source.videoWidth || source.duration < .25) {
    status('Choose a video with a known duration of at least a quarter second.');
    return;
  }
  element('start').value = '0';
  element('end').value = String(Math.floor(Math.min(30, source.duration) * 100) / 100);
  scrub.max = source.duration;
  const ratio = source.videoWidth / source.videoHeight;
  element('ratio').value = ratio < .72 ? '9:16' : ratio > .9 && ratio < 1.12 ? '1:1' : '4:5';
  canvas.hidden = false;
  element('empty').hidden = true;
  settings.disabled = false;
  scrub.disabled = false;
  resize();
  updateTime();
  status('Ready. Adjust the trim range or export this clip.');
});
source.addEventListener('error', () => {
  if (stopExport) stopExport(new Error('The source video stopped decoding.'));
  else if (inputUrl) status('This browser could not read the video. Try an MP4 with H.264 video and AAC audio.');
});
source.addEventListener('seeked', () => { draw(); updateTime(); });
scrub.addEventListener('input', () => { source.currentTime = Number(scrub.value); });
element('ratio').addEventListener('change', resize);
element('layout').addEventListener('change', draw);
element('caption').addEventListener('input', () => {
  if (element('caption-mode').value === 'auto') {
    const tokens = element('caption').value.trim().split(/\s+/).filter(Boolean);
    const start = element('start').valueAsNumber;
    const end = element('end').valueAsNumber;
    captionWords = tokens.map((text, index) => ({
      text,
      start: start + (end - start) * index / tokens.length,
      end: start + (end - start) * (index + 1) / tokens.length,
    }));
    captionKey = currentCaptionKey();
  }
  draw();
});
element('caption-mode').addEventListener('change', draw);
element('font').addEventListener('change', async () => {
  await document.fonts.load('700 32px "' + element('font').value + '"');
  draw();
});
const presets = {
  editorial: {font: 'Inter', layout: 'studio', ratio: '4:5', accent: '#95dfcb'},
  cinema: {font: 'Playfair Display', layout: 'fit', ratio: '16:9', accent: '#f5d29d'},
  minimal: {font: 'Poppins', layout: 'studio', ratio: '9:16', accent: '#ffffff'},
};
document.querySelectorAll('[data-preset]').forEach(button => button.addEventListener('click', async () => {
  const preset = presets[button.dataset.preset];
  element('font').value = preset.font;
  element('layout').value = preset.layout;
  element('ratio').value = preset.ratio;
  accent = preset.accent;
  document.querySelectorAll('[data-preset]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
  await document.fonts.load('700 32px "' + preset.font + '"');
  resize();
}));
element('start').addEventListener('change', () => {
  source.currentTime = Math.max(0, Math.min(source.duration, Number(element('start').value)));
});

function seek(time) {
  if (!source.seeking && Math.abs(source.currentTime - time) < .001) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      source.removeEventListener('seeked', ready);
      reject(new Error('Could not seek to the start of the clip.'));
    }, 5000);
    function ready() { clearTimeout(timeout); resolve(); }
    source.addEventListener('seeked', ready, {once:true});
    source.currentTime = time;
  });
}

function validRange() {
  const start = element('start').valueAsNumber;
  const end = element('end').valueAsNumber;
  if (!(start >= 0 && end <= source.duration && end - start >= .25 && end - start <= 120)) {
    throw new Error('Choose a valid trim range between 0.25 and 120 seconds long.');
  }
  return {start, end};
}

async function generateCaptions() {
  const {start, end} = validRange();
  if (captionKey === currentCaptionKey()) return;
  status('Preparing audio for English captions…');
  if (!decodedAudio) {
    decodedAudio = (async () => {
      const decoder = new AudioContext();
      try {
        return await decoder.decodeAudioData(await file.files[0].arrayBuffer());
      } finally {
        await decoder.close();
      }
    })();
  }
  let decoded;
  try {
    decoded = await decodedAudio;
  } catch {
    decodedAudio = undefined;
    throw new Error('This browser could not decode the audio. Choose My own caption or Captions off to export.');
  }
  const offline = new OfflineAudioContext(1, Math.ceil((end - start) * 16000), 16000);
  const track = offline.createBufferSource();
  track.buffer = decoded;
  track.connect(offline.destination);
  track.start(0, start, end - start);
  const waveform = (await offline.startRendering()).getChannelData(0);
  status('Loading speech model…');
  const id = ++generationId;
  if (!speechWorker) speechWorker = new Worker('caption-worker.js', {type: 'module'});
  cancel.hidden = false;
  progress.hidden = false;
  progress.removeAttribute('value');
  const result = await new Promise((resolve, reject) => {
    const worker = speechWorker;
    const timeout = setTimeout(() => fail(new Error('Caption generation timed out. Try a shorter clip or enter your own caption.')), 300000);
    function cleanup() {
      clearTimeout(timeout);
      worker.onmessage = worker.onerror = null;
      stopExport = null;
    }
    function fail(error) {
      cleanup();
      worker.terminate();
      speechWorker = undefined;
      reject(error);
    }
    stopExport = () => fail(new Error('Caption generation canceled.'));
    worker.onerror = event => {
      console.error('Speech worker failed:', event.message);
      fail(new Error('The speech model could not load. Check your connection or enter your own caption.'));
    };
    worker.onmessage = ({data}) => {
      if (data.id !== id) return;
      if (data.type === 'progress') status('Loading speech model for first use…');
      if (data.type === 'recognizing') status('Generating English captions…');
      if (data.type === 'error') {
        console.error('Speech processing failed:', data.detail);
        fail(new Error(data.message));
      }
      if (data.type === 'result') {
        cleanup();
        resolve(data);
      }
    };
    worker.postMessage({id, audio: waveform, language: element('language').value}, [waveform.buffer]);
  });
  const chunks = result.chunks || [];
  captionWords = chunks.flatMap((chunk, index) => {
    const tokens = chunk.text.trim().split(/\s+/).filter(Boolean);
    const from = Math.max(0, chunk.timestamp?.[0] ?? 0);
    const to = Math.min(end - start, chunk.timestamp?.[1] ?? chunks[index + 1]?.timestamp?.[0] ?? end - start);
    if (to <= from) return [];
    return tokens.map((text, i) => ({text, start: start + from + (to - from) * i / tokens.length, end: start + from + (to - from) * (i + 1) / tokens.length}));
  });
  if (!captionWords.length && result.text.trim()) {
    const tokens = result.text.trim().split(/\s+/);
    captionWords = tokens.map((text, i) => ({text, start: start + (end - start) * i / tokens.length, end: start + (end - start) * (i + 1) / tokens.length}));
  }
  captionKey = currentCaptionKey();
  element('caption').value = captionWords.map(word => word.text).join(' ');
  status(captionWords.length ? 'English captions ready. Review the text or export.' : 'No clear vocals were recognized. You can enter your own caption.');
  draw();
}

element('generate').addEventListener('click', async () => {
  settings.disabled = file.disabled = scrub.disabled = true;
  try {
    element('caption-mode').value = 'auto';
    await generateCaptions();
  } catch (error) {
    status(error.message);
  } finally {
    settings.disabled = file.disabled = scrub.disabled = false;
    cancel.hidden = progress.hidden = true;
  }
});

cancel.addEventListener('click', () => stopExport?.(new Error('Export canceled.')));
element('export').addEventListener('click', async () => {
  const start = element('start').valueAsNumber;
  const end = element('end').valueAsNumber;
  if (!(start >= 0 && end <= source.duration && end - start >= .25 && end - start <= 120)) {
    status('Choose a valid trim range between 0.25 and 120 seconds long.');
    return;
  }
  if (!window.MediaRecorder || !canvas.captureStream || !window.AudioContext) {
    status('This browser does not support clip export. Try opening this page in a current desktop browser.');
    return;
  }
  let videoTrack, frame, monitor, watchdog, recorder;
  settings.disabled = file.disabled = scrub.disabled = true;
  progress.hidden = false;
  progress.value = 0;
  status('Preparing export…');
  try {
    if (element('caption-mode').value === 'auto') await generateCaptions();
    await document.fonts.load('700 32px "' + element('font').value + '"');
    progress.value = 0;
    if (!audio) {
      audio = new AudioContext();
      audioDestination = audio.createMediaStreamDestination();
      audio.createMediaElementSource(source).connect(audioDestination);
    }
    await audio.resume();
    await seek(start);
    draw();
    const stream = canvas.captureStream(30);
    videoTrack = stream.getVideoTracks()[0];
    audioDestination.stream.getAudioTracks().forEach(track => stream.addTrack(track));
    const mimeType = ['video/mp4;codecs=avc1.42E01E,mp4a.40.2', 'video/mp4', 'video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm']
      .find(type => MediaRecorder.isTypeSupported(type));
    if (!mimeType) throw new Error('No compatible video encoder is available in this browser.');
    recorder = new MediaRecorder(stream, {mimeType, videoBitsPerSecond: 4_000_000});
    const blob = await new Promise((resolve, reject) => {
      const chunks = [];
      let failure;
      let stopping = false;
      stopExport = error => {
        if (stopping) return;
        stopping = true;
        failure = error;
        source.pause();
        if (recorder.state !== 'inactive') recorder.stop();
        else reject(error || new Error('Export stopped before recording started.'));
      };
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
      recorder.onerror = () => stopExport(new Error('The browser encoder could not finish this clip.'));
      recorder.onstop = () => {
        if (failure) reject(failure);
        else if (!chunks.length) reject(new Error('The encoder returned an empty clip.'));
        else resolve(new Blob(chunks, {type: recorder.mimeType || mimeType}));
      };
      watchdog = setTimeout(() => stopExport(new Error('Export timed out. Keep the editor tab active and retry.')), (end - start + 15) * 1000);
      cancel.hidden = false;
      status('Exporting in real time. Keep this tab open.');
      function tick() {
        draw();
        updateTime();
        progress.value = Math.min(1, (source.currentTime - start) / (end - start));
        if (source.currentTime >= end || source.ended) stopExport();
        else if (recorder.state === 'recording') frame = requestAnimationFrame(tick);
      }
      source.play().then(() => {
        if (stopping) { source.pause(); return; }
        draw();
        recorder.start(200);
        frame = requestAnimationFrame(tick);
        monitor = setInterval(() => {
          if (source.currentTime >= end || source.ended) stopExport();
        }, 40);
      }).catch(() => stopExport(new Error('Video playback could not start.')));
    });
    clearResult();
    outputUrl = URL.createObjectURL(blob);
    const extension = blob.type.startsWith('video/mp4') ? 'mp4' : 'webm';
    output.src = outputUrl;
    element('save').href = outputUrl;
    element('save').download = 'clipforge-clip.' + extension;
    element('result-meta').textContent = extension.toUpperCase() + ' · ' + canvas.width + ' × ' + canvas.height;
    element('result').hidden = false;
    element('result').scrollIntoView({block:'nearest'});
    status('Export complete. Play or save the finished clip below.');
  } catch (error) {
    status(error.message || 'Export failed.');
  } finally {
    clearInterval(monitor);
    clearTimeout(watchdog);
    cancelAnimationFrame(frame);
    source.pause();
    if (recorder && recorder.state !== 'inactive') recorder.stop();
    videoTrack?.stop();
    stopExport = null;
    progress.hidden = cancel.hidden = true;
    settings.disabled = file.disabled = scrub.disabled = false;
  }
});
