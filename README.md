Go to the fork below... It works for python3 / FreeCAD 0.18, 2019-May

https://github.com/looooo/FreeCAD_drawing_dimensioning.git


My fork is so that this works in OSX for FreeCAD 0.17

FreeCAD_drawing_dimensioning
============================

Drawing dimensioning workbench for FreeCAD v0.15.4576 and newer.
This workbench in not maintained.


Linux Installation Instructions
-------------------------------

For Ubuntu (Linux Mint) we recommend adding the community ppa to your systems software resources and install, via the sysnaptic package manager, the desired addon.

Refer here for more information:
https://launchpad.net/~freecad-community/+archive/ubuntu/ppa

On other Linux distros try to install manually via Terminal and git, replacing **apt-get** if not installed, with your distro's package manager:

```bash
$ sudo apt-get install git python-numpy python-pyside
$ mkdir ~/.FreeCAD/Mod
$ cd ~/.FreeCAD/Mod
$ git clone https://github.com/hamish2014/FreeCAD_drawing_dimensioning.git
```

Once installed, use git to easily update to the latest version:

```bash
$ cd ~/.FreeCAD/Mod/FreeCAD_drawing_dimensioning
$ git pull
$ rm *.pyc
```

Windows Installation Instructions
---------------------------------

Please use the FreeCAD-Addons-Installer provided here:
https://github.com/FreeCAD/FreeCAD-addons

For more in-depth information refer to the corresponding tutorial on the FreeCAD-Homepage:
http://www.freecadweb.org/wiki/index.php?title=How_to_install_additional_workbenches

Mac Installation Instructions
-----------------------------

Copy or unzip the drawing dimensioning folder to the directory *FreeCAD.app*/Contents/Mod
where *FreeCAD.app* is the folder where FreeCAD is installed. (thanks PLChris)

For more in-depth information refer to the corresponding tutorial on the FreeCAD-Homepage:
http://www.freecadweb.org/wiki/index.php?title=How_to_install_additional_workbenches


Testing
-------

```bash
$ cd ~/.FreeCAD/Mod/FreeCAD_drawing_dimensioning
$ python test
```

Acknowledgements
----------------

My thanks to BRLRFE and the other users who also contributed to this workbench.

Wiki
----

For instructions on usage of the workbench refer to the wiki (link on top of the page)
[https://github.com/hamish2014/FreeCAD_drawing_dimensioning/wiki]
