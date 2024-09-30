# OBS-Recording-Organizer
## Description
####
This is a fork of [francdv23's OBS Recordings Organizer](https://github.com/francdv23/OBS-Recordings-Organizer) and adds a few features, namely:
####
-The possibility to automatically cut replay buffers that overlap (with or without re-encoding the clips); it uses ffmpeg/ffprobe when saving a clip, thus in order to properly function it requires the built executables (i have put an already built binary inside the full release version).
### 
-The ability to choose whether to prefix the clip title with the game name or not (got the idea from [padiix](https://github.com/padiix/OBS-Recordings-Organizer)'s fork, thank you).
#### 
*Original Description:*
#### 
This is an improved and simplified version of [pjw29's OBS Rec Rename](https://github.com/pjw29/obs-rec-rename) Python script, that, similarly to NVidia ShadowPlay, allows OBS to rename and organize into folders video recordings based on the window title on focus whenever a replay buffer or a recording is saved, unlike from the previous version where it periodically checked for new clips.
## How to install
### Requirements
#### 
This script has been tested on Python 3.12 [(3.12.3 recommended)](https://www.python.org/downloads/release/python-3123/), as well as [pywin32](https://pypi.org/project/pywin32/) and [psutil](https://pypi.org/project/psutil/) libraries which can be installed via command line:
```
pip install pywin32
pip install psutil
```
Python can now be loaded in OBS by `Tools > Scripts > Python Settings` and choosing Python3123 path.
### Next steps
#### 
After the previous indications the actual script can be now installed. It doesn't need to be placed in a specific directory, for convenience the scripts folder located at `C:\Program Files\obs-studio\data\obs-plugins\frontend-tools\scripts\obs-rec-organizer` is ideal. It can be loaded into OBS by `Tools > Scripts` hit the *__"+"__* sign and search for _OBS-RecOrganizer.py_ from the previous path.
## Settings and configurations
### Basic
#### 
-Recordings folder: Default output folder when you hit Save Recording or Save Replay Buffer, can be found in your OBS settings.
#### 
-File extension: Default extension for the clip you save (the dot '.' is optional), this can be found in your OBS settings.
### Advanced
-Decollide Saved clips: makes sure saved recordings don't 'overlap' (i.e the previous clip shares some footage with the current clip, it's the default behaviour for Replay Buffer), this setting cuts the clip using ffmpeg to cut and ffprobe to get the video duration/s. If you don't check the option 'Don't Re-Encode when Decolliding' the decollided clip will loose some quality upon re-encoding.
#### 
-Don't Re-Encode when Decolliding: makes sure that ffmpeg doesn't re-encode the clip when decolliding it, thus keeping the clip's original quality. The caveat is that the cut is not precise: either a few extra frames are cut or they are kept, depending on where the nearest encoding keyframe lands in the clip relative to the cut timestamp.
#### 
-Custom FFMPEG exe path: path to the ffmpeg.exe file; optional, unless you downloaded the minimal release which doesn't contain it or you have a directory that contains ffmpeg.exe in your PATH.
#### 
-Custom FFPROBE exe path: path to the ffprobe.exe file; optional, unless you downloaded the minimal release which doesn't contain it or you have a directory that contains ffprobe.exe in your PATH.
#### 
### Overrides
#### 
Within the scripts are included two *cfg* files named *DesktopOverride.cfg* and *FullscreenOverride.cfg*, you can write the executable name in them to respectively override a windowed game targetting it correctly or to tweak a fullscreen program in *"Desktop"* recording.
## Common problems
#### 
1) If you experience any problems installing the libraries, the first thing I recommend to do is update pip with: 
```
python -m pip install --upgrade pip
```
2) If Pywin32 gives you any troubles, first uninstall it with ```pip uninstall pywin32``` and then download it from [here](https://github.com/mhammond/pywin32/releases/tag/b306) choosing *py312* version.
####
3) Recordings not organized into subfolder or not renamed: it can occur in the first/second recording or buffer replay, but no more further because the script only needed to create its cache.
