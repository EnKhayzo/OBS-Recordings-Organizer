import obspython as S
import glob, win32gui, win32process, re, psutil, os, os.path, shutil
from pathlib import Path
from ctypes import windll
from datetime import datetime, timedelta
import pathlib
import subprocess

# UTILS FUNCS
##############################

def strip_ext(path):
    lastIdx = path.rindex('.')
    if lastIdx == -1: return path
    return path[:lastIdx]

def get_ext(path):
    lastIdx = path.rindex('.')
    if lastIdx == -1 or lastIdx >= len(path)-1: return ''
    return path[lastIdx+1:]


def isQuote(ch):
    return ch == "\"" or ch == "'"

def isIgnorable(ch):
    return ch == ' ' or ch == '\n'

def getParam(inStr, n):
    res = None
    while len(inStr) > 0 and n >= 0:
        while(len(inStr) > 0 and isIgnorable(inStr[0])):
            inStr = inStr[1:]

        if len(inStr) > 0 and n == 0: res = ""

        if(len(inStr) > 0 and isQuote(inStr[0])):
            openingQuote = inStr[0]

            inStr = inStr[1:]
            while(len(inStr) > 0 and not inStr[0] == openingQuote):
                if n == 0: res += inStr[0]
                inStr = inStr[1:]
                
            if len(inStr) > 0: inStr = inStr[1:]
        else:
            while(len(inStr) > 0 and not isIgnorable(inStr[0])):
                if n == 0: res += inStr[0]
                inStr = inStr[1:]

        n-=1

    return res

def getParams(line):
    params = []

    n = 1
    param = getParam(line, 0)
    while param is not None:
        params.append(param)
        
        param = getParam(line, n)
        n+=1

    return params

def startProcess(command: str, onLine):
    print(command)

    args = None
    if not isinstance(command, list): args = getParams(command)
    else: args = command

    with subprocess.Popen(
        args, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT, 
        text=True, 
        shell=False, 
        encoding="utf-8",
        creationflags = subprocess.CREATE_NO_WINDOW
    ) as proc:
        for line in proc.stdout:
            ret = onLine(line.strip())
            if ret: break
            
    return proc.returncode


##############################
# /UTILS FUNCS


class Data:
    OutputDir = None
    Extension = None
    ExtensionMask = None

    PrefixGameName = None
    DecollideClips = None
    DontReencodeClips = None

    FFMPEGExePath = None
    FFPROBEExePath = None

    # non-property vars
    LastEndTimeStamp = None

def get_data_prefix_game_name():
    return Data.PrefixGameName if Data.PrefixGameName is not None else False

def get_data_extension():
    return Data.Extension.replace(".", "")

def get_dontreencode_clips():
    return Data.DontReencodeClips if Data.DontReencodeClips is not None else False

def get_ffmpeg_exe_path():
    ffmpeg_path = Data.FFMPEGExePath
    if ffmpeg_path is None or ffmpeg_path == '' or ffmpeg_path == "DEFAULT":
        ffmpeg_path = f"{script_path()}ffmpeg.exe"
        if not os.path.exists(ffmpeg_path):
            ffmpeg_path = "ffmpeg"
    res = ffmpeg_path
    print("ffmpeg_path",res)
    return res

def get_ffprobe_exe_path():
    ffprobe_path = Data.FFPROBEExePath
    if ffprobe_path is None or ffprobe_path == '' or ffprobe_path == "DEFAULT":
        ffprobe_path = f"{script_path()}ffprobe.exe"
        if not os.path.exists(ffprobe_path):
            ffprobe_path = "ffprobe"
    res = ffprobe_path
    print("ffprobe_path",res)
    return res

def get_video_metadata(video_path):
    """Get the metadata of a video file using ffprobe."""

    result = subprocess.run(
        [get_ffprobe_exe_path(), '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'format=duration:format_tags=creation_time', 
         '-of', 'default=noprint_wrappers=1', video_path], 
        shell=False,
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        creationflags = subprocess.CREATE_NO_WINDOW
    )
    output = result.stdout.decode('utf-8').strip().split('\n')
    
    duration = None
    creation_time = None

    for line in output:
        if line.startswith("duration="):
            duration = float(line.split('=')[1])
        if line.startswith("TAG:creation_time="):
            creation_time = line.split('=')[1]


    if creation_time:
        creation_time = datetime.strptime(creation_time, "%Y-%m-%dT%H:%M:%S.%fZ")

    if creation_time is None:
        creation_time = datetime.fromtimestamp(os.path.getmtime(video_path))

    return duration, creation_time

def cut_video(input_path, output_path, start_time, end_time):
    """Cut the video using ffmpeg."""

    os.makedirs(pathlib.Path(output_path).parent.resolve(), exist_ok=True)

    def onLine(line):
        pass
    return_code = 1
    if get_dontreencode_clips():
        return_code = startProcess([ 
            get_ffmpeg_exe_path(), 
            '-y', 
            '-ss', str(start_time), 
            '-to', str(end_time), 
            '-i', input_path,
            '-c', 'copy', 
            output_path 
        ], onLine)
    else:
        return_code = startProcess([ 
            get_ffmpeg_exe_path(), 
            '-y',
            '-ss', str(start_time), 
            '-to', str(end_time), 
            '-i', input_path, 
            output_path 
        ], onLine)

    if return_code != 0:
        print("ERROR!")

    return return_code


def find_previous_clip(target_clip, folder_path):
    target_clip_mtime = os.path.getmtime(target_clip)

    video_files = [ [ os.path.join(folder_path, f), os.path.getmtime(os.path.join(folder_path, f)) ] for f in os.listdir(folder_path)] # if "_decollide_cut." not in f and f.endswith(f".{get_data_extension()}") and f.startswith("ReplayBuffer_obs")]

    if len(video_files) <= 1: return None

    video_files.sort(key=lambda x: x[1])  # Sort by creation date
    
    previous_clip = None
    for file in video_files:
        if file[1] >= target_clip_mtime:
            break

        previous_clip = file[0]

    if previous_clip == target_clip: return None

    return previous_clip


def decollide_clip(target_clip, folder_path):
    previous_clip = find_previous_clip(target_clip, folder_path)
    if previous_clip is None: return

    prev_duration, prev_modify_time = get_video_metadata(previous_clip)
    prev_start_time = prev_modify_time - timedelta(seconds=prev_duration)
    prev_end_time = prev_modify_time

    curr_duration, curr_modify_time = get_video_metadata(target_clip)
    curr_start_time = curr_modify_time - timedelta(seconds=curr_duration)
    curr_end_time = curr_modify_time

    if curr_start_time.timestamp() < prev_end_time.timestamp():
        overlap_start = prev_end_time - curr_start_time

        output_path = os.path.join(folder_path, f"{strip_ext(target_clip)}_decollide_cut.{get_ext(target_clip)}")
        
        return_code = cut_video(target_clip, output_path, overlap_start.total_seconds(), curr_duration)

        if return_code == 0:
            os.remove(target_clip)
            print(f"Decollided clip '{target_clip}'.")
        else:
            print("error during clip decollision.")

def process_clip(event):
    target_clip = find_latest_file(Data.OutputDir, '\\*')

    dir = os.path.dirname(target_clip)
    rawfile = os.path.basename(target_clip)
    title = get_window_title()
    newFolder = f"{dir}\\{title}"

    name_prefix = f"{get_window_title()} " if get_data_prefix_game_name() else ""
    
    if not os.path.exists(newFolder):
        os.makedirs(newFolder)

    data_extension = get_data_extension()
    
    file =      f"{strip_ext(rawfile)}.{data_extension}"

    oldPath =   f"{dir}\\{file}"
    newfile =   f"{name_prefix}{strip_ext(rawfile)}.{data_extension}"
    newPath =   f"{newFolder}\\{newfile}"

    shutil.move(oldPath, newPath)
    print(f"moved '{oldPath}' to '{newPath}'")

    if(Data.DecollideClips):
        decollide_clip(newPath, newFolder)


def on_event(event):
    if event == S.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        print("Triggered when the recording stopped")
        process_clip(event)
    
    if event == S.OBS_FRONTEND_EVENT_REPLAY_BUFFER_SAVED:
        print("Triggered when the replay buffer saved")
        process_clip(event)


def get_window_title():
    user32 = windll.user32
    swd, sht = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)

    # Add in fullscreen detection here! 
    w = win32gui
    win_title = w.GetWindowText(w.GetForegroundWindow())
    
    l, t, r, b = w.GetWindowRect(w.GetForegroundWindow())
    wd, ht = r - l, b - t

    tid, pid = win32process.GetWindowThreadProcessId(w.GetForegroundWindow())
    p = psutil.Process(pid)
    exe = p.name()

    desktopOverride = 0
    fullscreenOverride = 0

    with open(script_path()+'/DesktopOverride.cfg') as dofile:
        if exe in dofile.read():
            desktopOverride = 1
    
    with open(script_path()+'/FullscreenOverride.cfg') as fsfile:
        if exe in fsfile.read():
            fullscreenOverride = 1

    if win_title[:3] == 'OBS':
        title = "Manual Recording"
    elif desktopOverride == 1:
        title = win_title
    else:
        if  wd == swd and ht == sht and fullscreenOverride == 0:
            title = win_title
        else:
            title = "Desktop"

    title = re.sub(r'[^0-9A-Za-z .-]', '', title)
    title = title[:50]

    return title.strip()



def find_latest_file(folder_path, file_type):
    files = glob.glob(folder_path + file_type)
    max_file = max(files, key=os.path.getmtime)
    return max_file



def script_load(settings):
    S.obs_frontend_add_event_callback(on_event)



def script_update(settings):
    print("update script settings")

    Data.OutputDir = S.obs_data_get_string(settings, "outputdir")
    Data.OutputDir = Data.OutputDir.replace('/','\\')
    Data.Extension = S.obs_data_get_string(settings, "extension")
    Data.ExtensionMask = '\\*' + Data.Extension

    Data.PrefixGameName = S.obs_data_get_bool(settings, "prefixgamename")
    Data.DecollideClips = S.obs_data_get_bool(settings, "decollideclips")
    Data.DontReencodeClips = S.obs_data_get_bool(settings, "dontreencodeclips")

    ffmpeg_path = S.obs_data_get_string(settings, "ffmpegpath")
    if ffmpeg_path == "DEFAULT":
        ffmpeg_path = f"{script_path()}\\ffmpeg.exe"
        if not os.path.exists(ffmpeg_path):
            ffmpeg_path = "ffmpeg"
    Data.FFMPEGExePath = ffmpeg_path

    ffprobe_path = S.obs_data_get_string(settings, "ffprobepath")
    if ffprobe_path == "DEFAULT":
        ffprobe_path = f"{script_path()}\\ffprobe.exe"
        if not os.path.exists(ffprobe_path):
            ffprobe_path = "ffprobe"
    Data.FFPROBEExePath = ffprobe_path



def script_description():
    # desc = "Renames and organizes recordings into subfolders like NVidia ShadowPlay.\n\nAuthor: francedv23, enkhayzo (added features)"
    desc = ("<h3>OBS Recording Organizer Upgraded <br> (<u>09.2024</u> update)</h3>"
            "<hr>"
            "Renames and organizes recordings into subfolders similar to NVIDIA ShadowPlay (<i>NVIDIA GeForce Experience</i>).<br><br>"
            "<small><a href='https://github.com/EnKhayzo/OBS-Recordings-Organizer'>GitHub repo link</a></small><br><br>"
            "<small>Original author:</small> <a href='https://obsproject.com/forum/resources/obs-recordings-organizer.1707/'><b>francedv23</b></a><br>"
            "<small>Updated by:</small> <b>enkhayzo</b><br><br>"
            "<small>Markup description by </small> <a href='https://github.com/padiix/OBS-Recordings-Organizer'><b>padii</b></a><small>'s fork (thank you)</small><br><br>"
            "<small>❤️ If you wish to support my work, i have a <a href='https://ko-fi.com/enkhayzo'>Ko-fi</a> page, thank you💕</small><br><br>"
            "<h4>Settings:</h4>")
    return desc


def script_properties():
    props = S.obs_properties_create()

    S.obs_properties_add_path(
        props, 
        "outputdir", 
        "Recordings folder", 
        S.OBS_PATH_DIRECTORY,
        None, 
        str(Path.home())
    )

    S.obs_properties_add_text(
        props,
        "extension",
        "File extension",
        S.OBS_TEXT_DEFAULT
    )

    S.obs_properties_add_bool(
        props,
        "prefixgamename",
        "Add game name as prefix",
    )

    decollide_bool = S.obs_properties_add_bool(
        props,
        "decollideclips",
        "Decollide Saved clips",
    )
    S.obs_property_set_long_description(decollide_bool, "makes sure saved recordings don't 'overlap' (i.e the previous clip shares some footage with the current clip, it's the default behaviour for Replay Buffer), this setting cuts the clip using ffmpeg to cut and ffprobe to get the video duration/s. If you don't check the option 'Don't Re-Encode when Decolliding' the decollided clip will loose some quality upon re-encoding.")

    dont_reencode_bool = S.obs_properties_add_bool(
        props,
        "dontreencodeclips",
        "Don't Re-Encode when Decolliding",
    )
    S.obs_property_set_long_description(dont_reencode_bool, "makes sure that ffmpeg doesn't re-encode the clip when decolliding it, thus keeping the clip's original quality. The caveat is that the cut is not precise: either a few extra frames are cut or they are kept, depending on where the nearest encoding keyframe lands in the clip relative to the cut timestamp.")

    ffmpeg_exe_path = S.obs_properties_add_path(
        props, 
        "ffmpegpath", 
        "Custom FFMPEG exe path", 
        S.OBS_PATH_FILE,
        "*.exe", 
        str("DEFAULT")
    )
    S.obs_property_set_long_description(ffmpeg_exe_path, "if not set, it looks for ffmpeg.exe in the script's folder; otherwise it checks for a directory that contains ffmpeg.exe in the PATH (akin to a normal CMD invokation 'ffmpeg ...')")

    ffprobe_exe_path = S.obs_properties_add_path(
        props, 
        "ffprobepath", 
        "Custom FFPROBE exe path", 
        S.OBS_PATH_FILE,
        "*.exe", 
        str("DEFAULT")
    )
    S.obs_property_set_long_description(ffprobe_exe_path, "if not set, it looks for ffprobe.exe in the script's folder; otherwise it checks for a directory that contains ffprobe.exe in the PATH (akin to a normal CMD invokation 'ffprobe ...')")

    return props