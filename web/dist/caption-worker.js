let engine;
let library;

self.onmessage = async ({data}) => {
  const {id, audio, language} = data;
  try {
    if (!library) library = import('https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.8.1');
    const {env, pipeline} = await library;
    env.allowLocalModels = false;
    env.backends.onnx.wasm.numThreads = 1;
    if (!engine) {
      engine = pipeline('automatic-speech-recognition', 'Xenova/whisper-tiny', {
        device: 'wasm',
        dtype: 'q8',
        progress_callback: () => self.postMessage({id, type: 'progress'}),
      });
    }
    const transcriber = await engine;
    self.postMessage({id, type: 'recognizing'});
    const options = {
      task: language === 'en' ? 'transcribe' : 'translate',
      return_timestamps: 'word',
      chunk_length_s: 30,
      stride_length_s: 5,
    };
    if (language !== 'auto') options.language = language;
    const result = await transcriber(audio, options);
    self.postMessage({id, type: 'result', text: result.text, chunks: result.chunks || []});
  } catch (error) {
    engine = undefined;
    library = undefined;
    self.postMessage({
      id,
      type: 'error',
      message: 'Speech processing could not finish. Check your internet connection for the model download, or choose My own caption and enter text.',
      detail: error.message,
    });
  }
};
