import io
import os
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from openai import OpenAI

from utils import ConfigManager

def create_local_model():
    """
    Create a local model using the faster-whisper library.
    """
    ConfigManager.console_print('Creating local model...')
    local_model_options = ConfigManager.get_config_section('model_options')['local']
    compute_type = local_model_options['compute_type']
    model_path = local_model_options.get('model_path')

    # Upstream forced int8 onto the CPU, which quietly kept every int8 setup off
    # the GPU even where CTranslate2 supports it - and int8 is the sensible
    # choice on cards without usable float16, so the rule ruled out exactly the
    # case it was needed for. The device is honoured as configured; a GPU that
    # cannot be used still falls back to the CPU below.
    device = local_model_options['device']
    ConfigManager.console_print(f'Model device: {device}, compute type: {compute_type}')

    name = model_path or local_model_options['model']
    if model_path:
        ConfigManager.console_print(f'Loading model from: {model_path}')

    try:
        model = _build_model(name, device, compute_type, bool(model_path))
    except Exception as e:
        if device == 'cpu':
            raise
        ConfigManager.console_print(f'Model on {device} unavailable: {e}')
        ConfigManager.console_print('Falling back to CPU.')
        model = _build_model(name, 'cpu', compute_type, bool(model_path))

    ConfigManager.console_print('Local model created.')
    return model

def _build_model(name, device, compute_type, is_path):
    """
    Load a model and prove it can actually run.

    Constructing a CUDA model succeeds on a machine with a driver but without
    the CUDA runtime libraries; it is the first encode that fails, with
    "Library cublas64_12.dll is not found". Left to itself that turns into a
    dead dictation halfway through, long after the point where falling back to
    the CPU was still possible. A two-frame encode settles it at startup, where
    the fallback is free.

    :param name: model name or a path to a converted model
    :param device: 'cpu', 'cuda' or 'auto'
    :param compute_type: quantisation to load the weights with
    :param is_path: True when name is a local path, so nothing is downloaded
    :return: a model that has completed one forward pass
    """
    model = WhisperModel(name, device=device, compute_type=compute_type,
                         download_root=None if is_path else None)
    silence = np.zeros(16000, dtype=np.float32)
    list(model.transcribe(silence, language='en')[0])
    return model


def _temperature_ladder(temperature):
    """
    Turn a single temperature into the retry ladder faster-whisper expects.

    faster-whisper defaults to [0.0, 0.2, ... 1.0]: it decodes at 0.0 and only
    retries at a higher temperature when the result trips its own garbage
    detectors - too repetitive, or too low an average log probability. Passing
    a bare number instead, which is what the config holds, silently turns that
    retry off, so a failed decode is returned as the answer.

    :param temperature: the configured temperature
    :return: a ladder starting at that temperature, or the value unchanged if
             it is already a sequence
    """
    if isinstance(temperature, (list, tuple)):
        return temperature
    start = temperature or 0.0
    return [t / 10 for t in range(int(start * 10), 11, 2)] or [start]


def transcribe_local(audio_data, local_model=None):
    """
    Transcribe an audio file using a local model.
    """
    if not local_model:
        local_model = create_local_model()
    model_options = ConfigManager.get_config_section('model_options')

    # Convert int16 to float32
    audio_data_float = audio_data.astype(np.float32) / 32768.0

    response = local_model.transcribe(audio=audio_data_float,
                                      language=model_options['common']['language'],
                                      initial_prompt=model_options['common']['initial_prompt'],
                                      condition_on_previous_text=model_options['local']['condition_on_previous_text'],
                                      temperature=_temperature_ladder(model_options['common']['temperature']),
                                      vad_filter=model_options['local']['vad_filter'],)
    return ''.join([segment.text for segment in list(response[0])])

def transcribe_api(audio_data):
    """
    Transcribe an audio file using the OpenAI API.
    """
    model_options = ConfigManager.get_config_section('model_options')
    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY') or None,
        base_url=model_options['api']['base_url'] or 'https://api.openai.com/v1'
    )

    # Convert numpy array to WAV file
    byte_io = io.BytesIO()
    sample_rate = ConfigManager.get_config_section('recording_options').get('sample_rate') or 16000
    sf.write(byte_io, audio_data, sample_rate, format='wav')
    byte_io.seek(0)

    response = client.audio.transcriptions.create(
        model=model_options['api']['model'],
        file=('audio.wav', byte_io, 'audio/wav'),
        language=model_options['common']['language'],
        prompt=model_options['common']['initial_prompt'],
        temperature=model_options['common']['temperature'],
    )
    return response.text

def post_process_transcription(transcription):
    """
    Apply post-processing to the transcription.
    """
    transcription = transcription.strip()
    post_processing = ConfigManager.get_config_section('post_processing')
    if post_processing['remove_trailing_period'] and transcription.endswith('.'):
        transcription = transcription[:-1]
    if post_processing['add_trailing_space']:
        transcription += ' '
    if post_processing['remove_capitalization']:
        transcription = transcription.lower()

    return transcription

def transcribe(audio_data, local_model=None):
    """
    Transcribe audio date using the OpenAI API or a local model, depending on config.
    """
    if audio_data is None:
        return ''

    if ConfigManager.get_config_value('model_options', 'use_api'):
        transcription = transcribe_api(audio_data)
    else:
        transcription = transcribe_local(audio_data, local_model)

    return post_process_transcription(transcription)

