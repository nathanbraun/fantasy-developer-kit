# 2024 Fantasy Football Developer Kit
These are the files for 2024 Fantasy Football Developer Kit. If you're reading
this and you *haven't* bought the 2024 kit yet, you can get it at
[https://fantasycoding.com](https://fantasycoding.com).

If you have, let's get started.  See installation instructions and then pick
back up in the guide.

## Installing
If you're not familiar with Git or GitHub, no problem. Just click the `Source
code` link under the latest release to download the files.  This will download
a file called `fantasy-developer-kit-vX.X.X.zip`, where X.X.X is the latest version
number.

When you unzip these (note in the book I've dropped the version number and
renamed the directory just `fantasy-developer-kit`, which you can do too) make
note of where you put them.

For example, on my mac, I have them in my home directory:

`/Users/nathanbraun/fantasy-developer-kit`

If I were using Windows, it might look like this:

`C:\Users\nathanbraun\fantasy-developer-kit`

To use these projects, you need to have an ini file called `config.ini`. I've
included an example (`config_example.ini`) for you to use as a starting point.

So the first step is renaming `config_example.ini` to just `config.ini`. Then
you can paste your developer kit license key in it. More details in the PDF
guide.

## Changelog
### v0.19.1 (2024-08-29)
Fix a few bugs in utilities/quickstart.

### v0.19.0 (2024-08-29)
Fix bug with ESPN leagues by updating the URL.

### v0.18.0 (2024-08-21)
Some fixes for 2024, with fixing Yahoo game id being a big one.

### v0.17.0 (2024-08-06)
Initial version for 2024 is ready! Reach out with any issues.

### v0.16.1 (2023-11-03)
Fix code to deal with ESPN API change.

### v0.16.0 (2023-09-20)
Update bestball chapter + include bestball/sleeper integration. Also a few
changes to sleeper integration.

### v0.15.0 (2023-09-18)
Update league integration walkthroughs for 2023 - ESPN, Fleaflicker, Yahoo,
Sleeper should all be working now. Let me know if issues.

### v0.14.3 (2023-09-16)
Take out a few recently added (but non essential) Python features that didn't
work with Python 3.9 (which is what is in Spyder).

### v0.14.2 (2023-09-15)
Fixed a few bugs in intro.py + added a note about Spyder (thanks Hanson!)

### v0.14.1 (2023-09-14)
Fix (sometimes) rounding issue in league.py (thanks Jonathan!)

### v0.14.0 (2023-09-13)
Major update: add final toos quickstart as first major thing we dive into. As
part of that, updated league integreation stuff + utilities behind the scenes.
Let me know if issues. Updated project walkthroughs coming soon.

### v0.13.1 (2023-09-07)
Initial update for 2023. Refactored (and improved) underlying simulations and
API. So far utilities.py, intro.py and the WDIS project are updated. Rest
coming ASAP.

### v0.12.1 (2022-09-29)
Fix bug in ESPN where things were failing if people hadn't played yet (thanks
Graydon!)

### v0.12.0
Allow year to be 2022.

### v0.11.0
Added instructions for using the Fantasy Math Web GUI.

### v0.10.0
Best ball project live and works with sample/example data.

### v0.9.0
League analysis project is live and works with sample/example data.

### v0.8.1
Add automatic check for `config.ini`.

### v0.8.0
League integration project is live and works with sample/example data. So you
should be able to follow along and do everything even if your own league hasn't
drafted yet. Once you work through it + draft, can update the tools to analyze
your own league.

### v0.7.0 
First project is live. Updated `intro.py` to use (optional) snapshot of data.

### v0.6.0 
Initial 2022 version. Includes through an introduction to the data. Projects
coming soon.
