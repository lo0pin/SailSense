import subprocess


POWER_HELPER = "/usr/local/sbin/sailsense-power"


def poweroff():
    """
    Fährt den Raspberry Pi kontrolliert herunter.
    Wird über ein begrenztes sudo-Hilfsskript ausgeführt.
    """
    subprocess.Popen(["sudo", POWER_HELPER, "poweroff"])


def reboot():
    """
    Startet den Raspberry Pi kontrolliert neu.
    """
    subprocess.Popen(["sudo", POWER_HELPER, "reboot"])
