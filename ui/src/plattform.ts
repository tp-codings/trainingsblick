/* Läuft die Oberfläche auf einem Mac? Dort heißen ein paar Dinge anders (⌘ statt Strg, kein Setup-Programm). */
export const MAC = /Mac/i.test(navigator.platform || navigator.userAgent);
