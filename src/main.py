import mido
import pyaudio
import threading
import time

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 1024

port_name = 'Portable Grand-1 0'    #TODO get port name - select from options in dialogue box?
midi_control = 64                   #TODO option to listen for midi activity, then 'choose' activated midi channel

audio = pyaudio.PyAudio()
pedal_state = False
recorded_frames = None

recording_thread = None
recording_thread_stop_event = threading.Event()
playback_thread = None
playback_thread_stop_event = threading.Event()

def record_audio():
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    
    print("Recording...")
    frames = []

    while not recording_thread_stop_event.is_set():  # Continue recording while pedal is pressed
        data = stream.read(CHUNK)
        frames.append(data)
        print("///RECORDING///")
    
    print("Finished recording.")
    stream.stop_stream()
    stream.close()
    
    global recorded_frames
    recorded_frames = frames

def play_audio():
    global recorded_frames
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, output=True)
    
    print("Playing back...")
    if recorded_frames:
        for frame in recorded_frames:
            if playback_thread_stop_event.is_set():
                print("playback thread stopped")
                break
            stream.write(frame)

        stream.stop_stream()
        stream.close()
        print("Finished playback.")
    else:
        print("no recorded frames")

def handle_pedal_events():
    global port_name, pedal_state, recorded_frames, playback_thread, midi_control, recording_thread, recording_thread_stop_event

    with mido.open_input(port_name) as port:
        for message in port:
            if (message.type == "control_change") and (message.control == midi_control):
                new_pedal_state = message.value > 0
                if new_pedal_state != pedal_state:  # accounts for multiple messages for a single event (some midi thing...?)
                    pedal_state = new_pedal_state
                    # print("control_change, now is: " + str(pedal_state))

                    if pedal_state:
                        print("ON")
                        if (playback_thread is not None) and (playback_thread.is_alive()):
                            playback_thread_stop_event.set()
                            playback_thread.join()
                            playback_thread = None

                        if (recording_thread is None) or (not recording_thread.is_alive()):
                            recording_thread_stop_event.clear()
                            recording_thread = threading.Thread(target=record_audio)
                            recording_thread.start()
                    else:
                        print( "OFF")
                        if (recording_thread is not None) and (recording_thread.is_alive()):
                            recording_thread_stop_event.set()
                            recording_thread.join()
                            recording_thread = None

                        if (playback_thread is None) or (not playback_thread.is_alive()):
                            playback_thread_stop_event.clear()
                            playback_thread = threading.Thread(target=play_audio)
                            playback_thread.start()

def start_playback():
    global playback_thread, playback_thread_stop_event
    playback_thread_stop_event.clear()
    playback_thread = threading.Thread(target=play_audio)
    playback_thread.start()

pedal_event_thread = threading.Thread(target=handle_pedal_events)
pedal_event_thread.start()

def monitor_recording():
    recording_thread_stop_event.wait()
    start_playback()

monitor_thread = threading.Thread(target=monitor_recording)
monitor_thread.start()