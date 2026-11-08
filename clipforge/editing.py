"""Correct short caption phrases in a local text editor."""
import os
import shlex
import subprocess
from pathlib import Path


def phrases(words: list[dict]) -> list[list[dict]]:
    return [words[index:index + 3] for index in range(0, len(words), 3)]


def apply_edits(words: list[dict], text: str) -> list[dict]:
    """Preserve phrase intervals, redistributing only edited words."""
    groups = phrases(words)
    lines = text.splitlines()
    if len(lines) != len(groups):
        raise ValueError('Keep the same number of caption lines; edit words within each line.')
    result = []
    for group, line in zip(groups, lines):
        if line == ' '.join(word['word'] for word in group):
            result.extend(group)
            continue
        tokens = line.split()
        if not tokens:
            continue
        start, end = group[0]['start'], group[-1]['end']
        step = (end - start) / len(tokens)
        result.extend({'word': word, 'start': start + index * step, 'end': start + (index + 1) * step} for index, word in enumerate(tokens))
    return result


def edit_captions(words: list[dict], path: Path) -> list[dict]:
    editor = os.getenv('EDITOR') or os.getenv('VISUAL') or ('notepad.exe' if os.name == 'nt' else None)
    if not editor:
        raise ValueError('Set EDITOR or VISUAL to edit captions.')
    if not words:
        raise ValueError('There are no caption words to edit.')
    path.write_text('\n'.join(' '.join(word['word'] for word in group) for group in phrases(words)) + '\n', encoding='utf-8')
    args = [arg.strip('"') for arg in shlex.split(editor, posix=os.name != 'nt')]
    subprocess.run([*args, str(path)], check=True)
    return apply_edits(words, path.read_text(encoding='utf-8-sig'))
