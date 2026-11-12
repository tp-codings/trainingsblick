# -*- coding: utf-8 -*-
"""
macOS-Schluesselbund (Keychain) ohne Zusatzpakete: Eintraege der Art "Passwort eines Programms" lesen, schreiben, loeschen.
Das Gegenstueck zur Windows-DPAPI in lib/tresor.py: der Schluesselbund "Anmeldung" ist mit dem Anmeldepasswort des
Mac-Benutzers verschluesselt, andere Benutzer und kopierte Ordner koennen nichts damit anfangen.

Angesprochen wird Security.framework direkt (ctypes), nicht das Kommando `security`: dort stuenden die Zugangsdaten kurz in
der Prozessliste, und jeder Aufruf von `security` duerfte sie ohne Nachfrage lesen. So gehoert der Eintrag dem Python,
das ihn angelegt hat; ein anderes Programm (oder ein ausgetauschtes Python nach einem Update) loest die uebliche
Nachfrage von macOS aus ("... moechte auf den Schluesselbund zugreifen").

Nur unter macOS importieren.
"""
from __future__ import annotations

import ctypes
from ctypes import c_char_p, c_int32, c_long, c_uint32, c_void_p

_sec = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
_cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")

_UTF8 = 0x08000100                  # kCFStringEncodingUTF8
NICHT_GEFUNDEN = -25300             # errSecItemNotFound
_DOPPELT = -25299                   # errSecDuplicateItem

_cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]
_cf.CFStringCreateWithCString.restype = c_void_p
_cf.CFDataCreate.argtypes = [c_void_p, c_char_p, c_long]
_cf.CFDataCreate.restype = c_void_p
_cf.CFDataGetLength.argtypes = [c_void_p]
_cf.CFDataGetLength.restype = c_long
_cf.CFDataGetBytePtr.argtypes = [c_void_p]
_cf.CFDataGetBytePtr.restype = c_void_p
_cf.CFDictionaryCreateMutable.argtypes = [c_void_p, c_long, c_void_p, c_void_p]
_cf.CFDictionaryCreateMutable.restype = c_void_p
_cf.CFDictionarySetValue.argtypes = [c_void_p, c_void_p, c_void_p]
_cf.CFDictionarySetValue.restype = None
_cf.CFRelease.argtypes = [c_void_p]
_cf.CFRelease.restype = None
_sec.SecItemAdd.argtypes = [c_void_p, c_void_p]
_sec.SecItemAdd.restype = c_int32
_sec.SecItemCopyMatching.argtypes = [c_void_p, ctypes.POINTER(c_void_p)]
_sec.SecItemCopyMatching.restype = c_int32
_sec.SecItemUpdate.argtypes = [c_void_p, c_void_p]
_sec.SecItemUpdate.restype = c_int32
_sec.SecItemDelete.argtypes = [c_void_p]
_sec.SecItemDelete.restype = c_int32


def _konstante(bibliothek, name):
    """Wert einer exportierten Konstante (ein CFTypeRef), z. B. kSecClass."""
    return c_void_p.in_dll(bibliothek, name).value


def _adresse(bibliothek, name):
    """Adresse einer exportierten Struktur, z. B. kCFTypeDictionaryKeyCallBacks."""
    return ctypes.addressof(c_void_p.in_dll(bibliothek, name))


class _Woerterbuch:
    """CFDictionary fuer eine Abfrage; gibt alles, was dafuer angelegt wurde, am Ende wieder frei."""

    def __init__(self, dienst=None, konto=None):
        self._frei = []
        self.ref = _cf.CFDictionaryCreateMutable(None, 0, _adresse(_cf, "kCFTypeDictionaryKeyCallBacks"),
                                                 _adresse(_cf, "kCFTypeDictionaryValueCallBacks"))
        self._frei.append(self.ref)
        if dienst is not None:
            self.fest("kSecClass", "kSecClassGenericPassword")
            self.text("kSecAttrService", dienst)
            self.text("kSecAttrAccount", konto)

    def fest(self, schluessel, wert, quelle=_sec):
        _cf.CFDictionarySetValue(self.ref, _konstante(_sec, schluessel), _konstante(quelle, wert))

    def text(self, schluessel, wert):
        s = _cf.CFStringCreateWithCString(None, str(wert).encode("utf-8"), _UTF8)
        self._frei.append(s)
        _cf.CFDictionarySetValue(self.ref, _konstante(_sec, schluessel), s)

    def daten(self, schluessel, wert):
        d = _cf.CFDataCreate(None, wert, len(wert))
        self._frei.append(d)
        _cf.CFDictionarySetValue(self.ref, _konstante(_sec, schluessel), d)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        for r in reversed(self._frei):
            if r:
                _cf.CFRelease(r)


def _fehler(was, status):
    return OSError("%s im Schlüsselbund fehlgeschlagen (Fehler %d)" % (was, status))


def lesen(dienst, konto):
    """Inhalt des Eintrags (bytes). OSError, wenn es ihn nicht gibt oder der Zugriff abgelehnt wurde."""
    with _Woerterbuch(dienst, konto) as q:
        q.fest("kSecReturnData", "kCFBooleanTrue", _cf)
        q.fest("kSecMatchLimit", "kSecMatchLimitOne")
        ergebnis = c_void_p()
        status = _sec.SecItemCopyMatching(q.ref, ctypes.byref(ergebnis))
    if status != 0 or not ergebnis.value:
        raise _fehler("Lesen", status)
    try:
        return ctypes.string_at(_cf.CFDataGetBytePtr(ergebnis), _cf.CFDataGetLength(ergebnis))
    finally:
        _cf.CFRelease(ergebnis)


def vorhanden(dienst, konto):
    """Gibt es den Eintrag? Fragt nur nach dem Eintrag, nicht nach dem Inhalt: das loest nie eine Nachfrage aus."""
    with _Woerterbuch(dienst, konto) as q:
        q.fest("kSecMatchLimit", "kSecMatchLimitOne")
        return _sec.SecItemCopyMatching(q.ref, None) == 0


def loeschen(dienst, konto):
    with _Woerterbuch(dienst, konto) as q:
        status = _sec.SecItemDelete(q.ref)
    if status not in (0, NICHT_GEFUNDEN):
        raise _fehler("Löschen", status)


def schreiben(dienst, konto, daten, beschriftung=""):
    """Eintrag anlegen oder ersetzen. Laesst sich ein vorhandener nicht aendern (er gehoert einem anderen Programm
    oder die Nachfrage wurde abgelehnt), wird er geloescht und neu angelegt."""
    with _Woerterbuch(dienst, konto) as q, _Woerterbuch() as neu:
        neu.daten("kSecValueData", daten)
        status = _sec.SecItemUpdate(q.ref, neu.ref)
    if status == 0:
        return
    if status != NICHT_GEFUNDEN:
        loeschen(dienst, konto)
    with _Woerterbuch(dienst, konto) as q:
        q.text("kSecAttrLabel", beschriftung or dienst)
        q.daten("kSecValueData", daten)
        status = _sec.SecItemAdd(q.ref, None)
    if status != 0:
        raise _fehler("Speichern", status)
