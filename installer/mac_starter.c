/*
 * Startprogramm der eigenstaendigen Mac-App (Trainingsblick.app/Contents/MacOS/Trainingsblick), gebaut von
 * installer/mac_bauen.py. Es laedt das Python, das in der App steckt (Contents/Resources/python), und fuehrt damit
 * Contents/Resources/app/trainingsblick.py aus. Weil das Programm selbst im Buendel liegt, erscheint es im Dock, in
 * der Menueleiste und in Nachfragen von macOS als "Trainingsblick".
 *
 * Abgeschottet (isolated): Umgebungsvariablen wie PYTHONPATH und Pakete im Benutzerordner bleiben aussen vor, es
 * zaehlt nur, was in der App liegt. sys.executable zeigt auf das Python in der App, damit der Garmin-Helfer
 * (lib/garmin_logik.py) es als eigenen Prozess starten kann.
 */
#include <Python.h>
#include <limits.h>
#include <mach-o/dyld.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int ende(PyConfig *c, PyStatus s)
{
    PyConfig_Clear(c);
    if (PyStatus_IsExit(s))
        return s.exitcode;
    Py_ExitStatusException(s);
    return 1;
}

int main(int argc, char **argv)
{
    char roh[PATH_MAX], inhalt[PATH_MAX], heim[PATH_MAX], python[PATH_MAX], skript[PATH_MAX];
    uint32_t n = sizeof roh;
    char *p;
    int i;

    if (_NSGetExecutablePath(roh, &n) != 0 || !realpath(roh, inhalt))
        return 111;
    for (i = 0; i < 2; i++) {               /* .../Contents/MacOS/Trainingsblick -> .../Contents */
        if (!(p = strrchr(inhalt, '/')))
            return 111;
        *p = 0;
    }
    snprintf(heim, sizeof heim, "%s/Resources/python", inhalt);
    snprintf(python, sizeof python, "%s/Resources/python/bin/python3", inhalt);
    snprintf(skript, sizeof skript, "%s/Resources/app/trainingsblick.py", inhalt);

    /* nichts in die App schreiben (auch nicht der Garmin-Helfer): sonst passt ihre Signatur nicht mehr */
    setenv("PYTHONDONTWRITEBYTECODE", "1", 1);

    PyConfig c;
    PyStatus s;
    PyConfig_InitIsolatedConfig(&c);
    c.write_bytecode = 0;
    c.safe_path = 0;                        /* Ordner des Skripts in sys.path, wie bei "python trainingsblick.py" */
    if (PyStatus_Exception(s = PyConfig_SetBytesString(&c, &c.home, heim)))
        return ende(&c, s);
    if (PyStatus_Exception(s = PyConfig_SetBytesString(&c, &c.executable, python)))
        return ende(&c, s);
    if (PyStatus_Exception(s = PyConfig_SetBytesString(&c, &c.run_filename, skript)))
        return ende(&c, s);
    argv[0] = skript;                       /* sys.argv = [trainingsblick.py, Argumente ...] */
    if (PyStatus_Exception(s = PyConfig_SetBytesArgv(&c, argc, argv)))
        return ende(&c, s);
    if (PyStatus_Exception(s = Py_InitializeFromConfig(&c)))
        return ende(&c, s);
    PyConfig_Clear(&c);
    return Py_RunMain();
}
