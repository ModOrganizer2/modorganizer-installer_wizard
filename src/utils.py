from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from wizard.tweaks import WizardINISetting, WizardINISettingEdit


def make_obscript_ini_tweaks(tweaks: Sequence[WizardINISetting]) -> str:
    lines: list[str] = []

    for tweak in tweaks:
        if not isinstance(tweak, WizardINISettingEdit):
            continue
        line = f"{tweak.section} {tweak.setting} to {tweak.value}"
        if tweak.comment:
            line += f" ; {tweak.comment}"

        lines.append(line)

    return "\n".join(["; Generated by Mod Organizer 2 via Wizard"] + sorted(lines))


def make_standard_ini_tweaks(tweaks: Sequence[WizardINISetting]) -> str:
    # group Tweaks per section
    sections: dict[str, list[WizardINISetting]] = {m.section: [] for m in tweaks}
    for m in tweaks:
        sections[m.section].append(m)

    lines: list[str] = []

    for k in sorted(sections):
        s_tweaks = sorted(sections[k], key=lambda m: m.setting)
        lines.append(f"[{k}]")
        for tw in s_tweaks:
            if isinstance(tw, WizardINISettingEdit):
                line = f"{tw.setting} = {tw.value}"
                if tw.comment:
                    line += f" # {tw.comment}"
            else:
                line = f"# {tw.setting} - disabled"
            lines.append(line)
        lines.append("\n")

    return "\n".join(lines[:-1])


def merge_standard_ini_tweaks(tweaks: Sequence[WizardINISetting], file: Path) -> str:
    import sys

    print(f"Cannot merge INI Tweaks for {file.name}.", file=sys.stderr)
    return make_standard_ini_tweaks(tweaks)


def merge_obscript_ini_tweaks(tweaks: Sequence[WizardINISetting], file: Path) -> str:
    # this is from Wrye Bash (and the function is inspired from Wrye Bash)
    reComment = re.compile(";.*", re.U)
    reDeleted = re.compile("" r";-(\w.*?)$", re.U)
    reSet = re.compile("" r"\s*set\s+(.+?)\s+to\s+(.*)", re.I | re.U)
    reSetGS = re.compile("" r"\s*setGS\s+(.+?)\s+(.*)", re.I | re.U)
    reSetNGS = re.compile("" r"\s*SetNumericGameSetting\s+(.+?)\s+(.*)", re.I | re.U)

    _regex_tuples = (
        (reSet, "set", "set {} to {}"),
        (reSetGS, "setgs", "setGS {} {}"),
        (reSetNGS, "setnumericgamesetting", "SetNumericGameSetting {} {}"),
    )

    def _parse_obse_line(line: str):
        for regex, sectionKey, format_string in _regex_tuples:
            match = regex.match(line)
            if match:
                return match, sectionKey, format_string
        return None, None, None

    # read the original file
    with open(file, "r") as fp:
        olines = fp.readlines()

    # map setting name to value
    settings: dict[str, dict[str, WizardINISettingEdit]] = {}
    deleted: dict[str, dict[str, WizardINISetting]] = {}
    for tweak in tweaks:
        if isinstance(tweak, WizardINISettingEdit):
            if tweak.section not in settings:
                settings[tweak.section.lower()] = {}
            settings[tweak.section.lower()][tweak.setting] = tweak
        else:
            if tweak.section not in deleted:
                deleted[tweak.section.lower()] = {}
            deleted[tweak.section.lower()][tweak.setting] = tweak

    # create the lines
    lines: list[str] = []
    for line in olines:
        line = line.rstrip()
        maDeleted = reDeleted.match(line)
        if maDeleted:
            stripped = maDeleted.group(1)
        else:
            stripped = line
        stripped = reComment.sub("", stripped).strip()

        match, section_key, format_string = _parse_obse_line(stripped)

        if match:
            assert format_string is not None
            setting = match.group(1)
            if section_key in settings and setting in settings[section_key]:
                value = settings[section_key][setting].value
                line = format_string.format(setting, value)
                comment = ""
                if settings[section_key][setting].comment:
                    comment = cast(str, settings[section_key][setting].comment)
                    comment += " "
                comment += f"(set by MO2 via Wizard, was {match.group(2)})"
                line = f"{line}  ; {comment}"
                del settings[section_key][setting]
            elif (
                not maDeleted
                and section_key in deleted
                and setting in deleted[section_key]
            ):
                line = f";-{line}"

        lines.append(line)

    for section in settings.values():
        line = ""
        for setting in section.values():
            if setting.section.lower() == "set":
                line = f"{setting.section} {setting.setting} to {setting.value}"
            else:
                line = f"{setting.section} {setting.setting} {setting.value}"

            if setting.comment:
                comment = setting.comment + " (set by MO2 via Wizard)"
            else:
                comment = "(set by MO2 via Wizard)"
            line = f"{line}  ; {comment}"

        lines.append(line)

    return "\n".join(lines)


def make_ini_tweaks(tweaks: Sequence[WizardINISetting]) -> str:
    is_set = [
        tw.section.lower() in ("set", "setgs", "setnumericgamesetting") for tw in tweaks
    ]

    # assume there is no mix
    if all(is_set):
        return make_obscript_ini_tweaks(tweaks)
    else:
        return make_standard_ini_tweaks(tweaks)


def merge_ini_tweaks(tweaks: Sequence[WizardINISetting], file: Path) -> str:
    is_set = [
        tw.section.lower() in ("set", "setgs", "setnumericgamesetting") for tw in tweaks
    ]

    # assume there is no mix
    if all(is_set):
        return merge_obscript_ini_tweaks(tweaks, file)
    else:
        return merge_standard_ini_tweaks(tweaks, file)
