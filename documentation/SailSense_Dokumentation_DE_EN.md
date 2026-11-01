# SailSense

## A compact, open-source sailing data logger and environmental monitoring system
### Bilingual project documentation · German / English · Prototype status: 1 November 2026

**Project:** SailSense  
**Platform:** Raspberry Pi Zero 2 W · Python · GPS/GNSS · BME280 · OLED · GPIO  
**Design:** Custom enclosure in Autodesk Fusion; 3D-print preparation in Bambu Studio  
**Source basis:** `SailSense.zip`, `sailsense.f3d`, `sailsense.3mf` and the accompanying prototype and CAD photographs  
**Development stage:** Functional software prototype; enclosure and several hardware interfaces remain under development

> **Editorial note / Redaktioneller Hinweis:** This is project documentation for an illustrated publication, not a certified technical manual. Figure references point to files in `images/`. The text reflects the supplied software snapshot, not an independently verified on-board acceptance test. / Dies ist die Textgrundlage für eine bebilderte Projektdokumentation, keine zertifizierte technische Betriebsanleitung. Die Bildverweise beziehen sich auf den Ordner `images/`. Beschrieben ist der übermittelte Code-Stand, nicht eine unabhängig geprüfte Abnahme auf einem Segelboot.

---

# TEIL I — DEUTSCH

## 1. Die Idee hinter SailSense

Auf einem Segelboot entstehen fortlaufend Informationen, die während des Törns interessant und im Nachhinein wertvoll sind: der tatsächlich gesegelte Kurs, die zurückgelegte Distanz, die Entwicklung des Luftdrucks oder die Veränderungen von Temperatur und Luftfeuchtigkeit. Ein Teil davon ist auf Kartenplottern, Smartphones und Wetterstationen sichtbar. Die Daten bleiben jedoch häufig auf unterschiedliche Geräte und Anwendungen verteilt. Genau hier setzt **SailSense** an.

SailSense ist ein selbst entwickeltes, Raspberry-Pi-basiertes Mess- und Aufzeichnungssystem für den Einsatz an Bord. Es kombiniert einen GPS-Empfänger zur Erfassung von Position und Bewegung mit einem BME280-Umweltsensor, einer kleinen OLED-Anzeige und einer einfachen Bedienoberfläche. Hinzu kommen optische und akustische Signale, eine GPS-basierte Ankerwache und die Möglichkeit, aufgezeichnete Strecken als GPX-Dateien weiterzuverwenden.

Das Projekt verfolgt bewusst nicht das Ziel, einen professionellen Kartenplotter zu ersetzen. SailSense ist vielmehr ein unabhängiges, kompaktes Zusatzinstrument: ein kleines elektronisches Logbuch, ein Barograph und eine experimentelle Plattform, auf der sich Sensorik, Programmierung und mechanische Konstruktion miteinander verbinden lassen. Der angestrebte Betrieb ist weitgehend autonom. Das Gerät soll im Hintergrund weiter messen und speichern, auch wenn gerade kein Smartphone in der Nähe ist.

Die Entwicklung ist zugleich ein klassisches Maker-Projekt. Elektronik, Python-Software, praktische Messtechnik und CAD-Konstruktion greifen ineinander. Der offen aufgebaute Versuchsstand zeigt, dass das System zunächst modular erprobt wurde, bevor die Integration in ein maßgeschneidertes Gehäuse begann. Diese Iteration ist kein Nebenschauplatz: Eine Messstation für die Kajüte muss nicht nur funktionieren, sondern sich auch befestigen, bedienen, versorgen und gegen die widrigen Bedingungen auf See schützen lassen.

**Bildhinweis D01 – Elektronischer Versuchsaufbau:** `images/01_prototype_breadboard.jpg`  
*Bildunterschrift: Früher SailSense-Prototyp auf Breadboard mit Raspberry Pi, Leitungsverbindungen und angeschlossener Peripherie. Die offene Anordnung erleichtert Fehlersuche und Funktionsprüfungen, ist jedoch noch kein bordtauglicher Endaufbau.*

## 2. Zielsetzung und Projektphilosophie

Drei Anforderungen prägen das Konzept. Erstens sollen **Messdaten möglichst nachvollziehbar** bleiben. Positionen und Umweltwerte werden in lesbaren CSV-Dateien gespeichert; GPS-Tracks lassen sich zusätzlich in das verbreitete GPX-Format exportieren. Die spätere Auswertung ist damit nicht an eine bestimmte App oder Cloud-Plattform gebunden.

Zweitens ist **praktische Bedienbarkeit** entscheidend. Vier Taster, ein kleines Display, eine mehrfarbige LED und ein Summer reichen grundsätzlich aus, um wichtige Funktionen ohne Touchscreen zu kontrollieren: einen Track starten oder stoppen, einen Marker setzen, den Luftdruckverlauf betrachten oder die Ankerwache einschalten. Die Gestaltung soll gerade dort sinnvoll bleiben, wo ein Smartphone unpraktisch ist – etwa bei Nässe, Dunkelheit oder einer schnellen Kontrolle zwischendurch.

Drittens soll das System **ausbaufähig** bleiben. Die Software ist in Komponenten für GPS, Wetter, Darstellung, Speicherung, Ausgabe und Bedienung gegliedert. Ergänzungen wie eine inertiale Messeinheit (MPU/IMU), ein stromsparenderer Betriebsmodus oder eine lokale Weboberfläche sind damit architektonisch naheliegend, gehören aber nicht vollständig zum gegenwärtigen Funktionsumfang.

Die Leitidee lautet: möglichst viele nützliche Informationen bei möglichst geringer Komplexität und überschaubarem Energieverbrauch. Zwischen diesen Zielen bestehen Zielkonflikte. Ein dauerhaft leuchtendes Display erhöht den Komfort, verbraucht aber Energie. Ein hermetisch abgeschlossenes Gehäuse schützt die Elektronik, erschwert jedoch korrekte Temperatur- und Feuchtemessungen. Die Dokumentation macht diese Kompromisse ausdrücklich sichtbar.

## 3. Hardware: Aufbau und zentrale Komponenten

Das Rechenzentrum ist ein **Raspberry Pi Zero 2 W**. Er bietet ausreichend Rechenleistung für das Einlesen serieller GPS-Daten, die Abfrage des I²C-Sensors, die grafische Darstellung und das kontinuierliche Schreiben von Messdateien. Sein kleiner Formfaktor begünstigt ein kompaktes Gehäuse; die integrierte WLAN-Funktion eröffnet außerdem die Möglichkeit einer späteren Bedienung über das lokale Netz.

Die wesentlichen Funktionsgruppen des vorliegenden Prototyps sind:

| Baugruppe | Aufgabe | Schnittstelle / Stand |
|---|---|---|
| Raspberry Pi Zero 2 W | Zentrale Verarbeitung, Dateisystem, Python-Anwendung | Implementiert |
| USB-GPS/GNSS-Empfänger | Position, Geschwindigkeit, Kurs und GPS-Zeit | Seriell über USB; im Code `/dev/ttyACM0`, 9600 Baud |
| Bosch BME280 | Temperatur, relative Feuchte, Luftdruck | I²C, konfigurierte Adresse `0x76` |
| OLED 128 × 64 Pixel | Statusinformationen, Menüs, Wettergraphen, Trackskizze | I²C, konfigurierte Adresse `0x3C` |
| Vier Taster | Hoch, Runter, Bestätigen, Zurück | GPIO 17, 27, 22, 23 (BCM) |
| RGB-Status-LED | Status, Warnzonen, weißes/rotes Licht | GPIO 5, 6, 13; gemeinsame Anode |
| Passiver Summer | Bestätigungen, Warnungen, Ankeralarm | GPIO 12 |
| MPU/IMU | Potenzielle Bewegungs- und Lagedaten | In der Konfiguration vorgesehen; **nicht integriert** |
| Externe USB-Versorgung | Stromversorgung | Prototypisch erprobt; finale Energiearchitektur offen |

Die oben genannten Pin-Nummern sind **BCM-GPIO-Nummern, keine physischen Pinpositionen** der Raspberry-Pi-Stiftleiste. Maßgeblich ist die im ZIP enthaltene `config/settings.yaml`. Die GPIO-Beschaltung darf nur mit geeigneten Spannungen und Vorwiderständen erfolgen; die Raspberry-Pi-Eingänge sind nicht 5-V-tolerant. Der konkrete elektrische Schaltplan einschließlich aller Bauteilwerte sollte als eigenständige Datei ergänzt werden.

Bei I²C teilen sich BME280 und OLED grundsätzlich die Busleitungen SDA (GPIO 2) und SCL (GPIO 3), sofern keine abweichende Hardwarekonfiguration eingesetzt wird. Gerade die Displayintegration erwies sich in der Entwicklung als sensible Stelle: Ein Modul, das mechanisch ähnlich aussieht, muss nicht zwangsläufig denselben Controller, dieselbe Adresse oder dieselbe Pinbelegung besitzen. Deshalb enthält das Projekt separate Testprogramme, um Peripherie schrittweise prüfen zu können.

**Bildhinweis D02 – Raspberry Pi und GPIO:** `images/02_raspberry_pi_wiring.jpg`  
*Bildunterschrift: Raspberry Pi Zero 2 W mit angeschlossenen GPIO-Leitungen. Bereits im offenen Prototyp ist die Aufteilung auf serielle GPS-Verbindung, I²C und diskrete Ein-/Ausgänge erkennbar.*

**Bildhinweis D03 – Displaytest:** `images/03_oled_startup.jpg`  
*Bildunterschrift: Monochromes OLED während des Programmstarts. Die kompakte Anzeige liefert Rückmeldungen ohne angeschlossenen Monitor.*

## 4. Softwarearchitektur und Programmablauf

SailSense ist überwiegend in **Python** umgesetzt. Die Anwendung folgt einem modularen Aufbau unter `src/sailsense/`. Der zentrale Einstiegspunkt für die vollständige Geräteoberfläche ist `sailsense.app`; daneben existieren bewusst einfachere Logger und Hardwaretests. Die Hauptanwendung verbindet die Sensoren, die Benutzereingaben und die Ausgabekomponenten in einer fortlaufenden Programmschleife.

Die wichtigsten Bestandteile sind:

- `gps/`: NMEA-Einlesen, Distanzberechnung und Verwaltung einzelner GPS-Track-Sitzungen.
- `weather/`: BME280-Treiber, Mittelwertbildung, Langzeitverlauf und Wiederladen gespeicherter Messungen.
- `display/`: OLED-Ansteuerung, Wetterkurven und einfache grafische Trackdarstellung.
- `anchor/`: GPS-basierte Ankerwache mit abgestuften Warn- und Alarmzonen.
- `input/` und `output/`: Taster, RGB-LED und Summer.
- `storage/` und `export/`: CSV-Dateien, Trackindex und GPX-Ausgabe.
- `runtime_settings.py`: Einstellungen, die am Gerät verändert und teilweise dauerhaft in YAML gespeichert werden können.
- `system/`: Aufruf eines vorgesehenen privilegierten Hilfsprogramms für Neustart und Herunterfahren.
- `imu/`: derzeit lediglich ein vorbereitetes Modulverzeichnis.

Beim Start werden Konfiguration und Laufzeitzustand geladen. Die Anwendung initialisiert GPS, BME280, OLED, Taster, LED und Summer, lädt vorhandene Wetterhistorie und die Liste abgeschlossener Tracks und zeigt anschließend die Hauptoberfläche. Während des Betriebs prüft die Schleife neue GPS-Sätze und Sensorwerte, führt gegebenenfalls die Ankerwachenlogik aus, aktualisiert die Anzeige und schreibt Daten auf den Datenträger.

Das Programm ist auf dem Raspberry Pi als **systemd-Dienst** vorgesehen. Ein automatischer Dienststart kann SailSense nach dem Einschalten ohne angeschlossene Tastatur oder Monitor verfügbar machen. Der aktuelle Quellcode enthält Startskripte, jedoch keine vollständig mitgelieferte, allgemein installierbare Dienst- und Installationskonfiguration. Das sollte vor einer Veröffentlichung als einfach reproduzierbares System ergänzt werden.

Der Quellcode ist kein Beweis für vollständige Gerätezuverlässigkeit: Das ZIP lässt sich syntaktisch als Python-Quelltext prüfen, die reale Interaktion der angeschlossenen Bauteile und ein lückenloser Langzeitbetrieb müssen aber auf der Hardware validiert werden.

## 5. GPS-Logger und elektronisches Törnprotokoll

Der GPS-Teil liest NMEA-Daten aus der seriellen Verbindung. Er verarbeitet insbesondere **GGA-Sätze** für Informationen wie Satellitenzahl, Fixqualität, HDOP und Höhe sowie gültige **RMC-Sätze** für Zeitpunkt, Position, Geschwindigkeit über Grund und Kurs über Grund. Ungültige RMC-Positionen werden verworfen. Gespeichert werden UTC-Zeitstempel und geographische Koordinaten sowie ergänzende Qualitäts- und Bewegungswerte.

Eine Trackaufzeichnung wird über die Geräteoberfläche ausdrücklich gestartet. Für jede Sitzung legt SailSense eine eigene CSV-Datei an. Im vorliegenden Konfigurationsstand beträgt das Mindestintervall zwischen geschriebenen Trackpunkten **fünf Sekunden**. Die Trackverwaltung berücksichtigt eine Mindestzahl von **fünf Satelliten** und einen HDOP-Grenzwert von **5,0**; einzelne Positionssprünge von mehr als **500 Metern** gegenüber dem letzten akzeptierten Punkt werden unterdrückt. Diese einfache Plausibilitätskontrolle reduziert auffällige Fehlmessungen, ersetzt jedoch keine umfassende Navigationserkennung oder professionelle GNSS-Filterung.

Die zurückgelegte Distanz wird aus aufeinanderfolgenden akzeptierten Positionen über die Haversine-Formel berechnet. Intern erfolgt die Berechnung in Metern; für die nautische Anzeige werden die Werte in **Seemeilen (1 sm = 1.852 m)** umgerechnet. Während der Aufzeichnung zeigt das Gerät unter anderem Dauer, Distanz und Punktzahl. Über die OK-Taste lassen sich außerdem Marker für einzelne besondere Stellen im Track hinterlegen.

Beim regulären Beenden schreibt das Programm einen Eintrag in den Trackindex und versucht automatisch, die CSV-Aufzeichnung als **GPX 1.1** zu exportieren. Die GPX-Datei enthält die standardisierten Positions-, Zeit-, Höhen- und – soweit vorhanden – Satelliten- und HDOP-Felder. Zusätzliche Angaben wie Geschwindigkeit, Kurs, zurückgelegte Teilstrecken und Marker werden als eigene XML-Erweiterungen abgelegt. Allgemeine GPX-Viewer können diese Zusatzfelder ignorieren; die grundlegende Route bleibt trotzdem in einem verbreiteten Austauschformat verfügbar.

Das OLED ermöglicht außerdem das Durchblättern gespeicherter Tracks und eine auf den Displayausschnitt skalierte, nordorientierte Trackskizze. Diese Darstellung ist bewusst minimalistisch: Sie dient der Orientierung und Rückschau, **nicht** als Ersatz für eine Seekarte oder einen verlässlichen Kartenplotter.

Eine technische Grenze ist wichtig: Die aktuelle Track-Sitzung wird erst beim ordentlichen Stoppen vollständig im Index abgeschlossen. Bei einem Stromausfall können die bis dahin geschriebenen CSV-Zeilen vorhanden sein, der Trackindex und der automatische GPX-Export fehlen aber möglicherweise. Eine Wiederherstellungsfunktion für unvollständig beendete Tracks ist daher ein vorrangiger Entwicklungsschritt.

## 6. Wetteraufzeichnung und Barograph

Der BME280 liefert drei Messgrößen: **Temperatur in °C**, **relative Luftfeuchtigkeit in Prozent** und **Luftdruck in hPa**. Der vorhandene Wetterdienst verwendet dafür unterschiedliche Zeitmaßstäbe, um kurzfristige Anzeige und langfristige Beobachtung voneinander zu trennen.

In der mitgelieferten Konfiguration wird der Sensor grundsätzlich alle **10 Sekunden** ausgelesen. Für die Anzeige bildet SailSense einen gleitenden Mittelwert über ungefähr **60 Sekunden**; für die Langzeitspeicherung wird in der Regel alle **15 Minuten** ein Durchschnitt aus den seit dem letzten Speichervorgang gesammelten Messwerten geschrieben. Bei 96 gespeicherten Viertelstundenwerten entsteht ein Verlauf von ungefähr **24 Stunden**. Beim Programmstart werden ältere Messungen nachgeladen, damit die Kurve nicht jedes Mal bei null beginnt. In einer Testumgebung lässt sich das Speicherraster über `SAILSENSE_WEATHER_STORAGE_INTERVAL` in Sekunden überschreiben.

Der Barograph stellt den zeitlichen Verlauf des Luftdrucks auf dem kleinen OLED als Kurve dar. Ergänzend gibt es graphische Ansichten für Temperatur und relative Feuchtigkeit. Besonders interessant ist die manuell einstellbare **Referenzlinie**: Statt die Mittellinie immer an den Mittelwert des sichtbaren Verlaufs zu koppeln, kann der Nutzer beispielsweise **1013 hPa** als festen Bezug vorgeben. Die Werte erscheinen dann bewusst ober- und unterhalb dieser Referenz. Auch der vertikale Maßstab ist einstellbar, etwa auf **0,25 hPa pro Pixel**, und wird auf der Anzeige kenntlich gemacht. Der Code bietet dafür verschiedene diskrete Zoomstufen.

Damit ist der Barograph nicht bloß eine dekorative Kurve. Ein fester Bezug erlaubt es, Luftdruckänderungen über mehrere Ansichten hinweg vergleichbar wahrzunehmen, während die explizite Pixel-Skalierung die Größenordnung der Abweichungen offenlegt. Dennoch ist ein Luftdrucktrend **keine eigenständige Wettervorhersage**: Lokale Bedingungen, Zugbahnen, Fronten und andere meteorologische Informationen müssen berücksichtigt werden.

Für die Qualität der Umweltmessungen ist der **Einbauort** entscheidend. Befindet sich der Sensor unmittelbar über dem Raspberry Pi oder in einem schlecht belüfteten Kunststoffgehäuse, kann die Eigenwärme der Elektronik insbesondere die Temperaturmessung verfälschen und indirekt die relative Feuchte beeinflussen. Die im CAD vorgesehene Gitteröffnung und die separate Sensorhalterung sind deshalb konstruktiv ebenso relevant wie die Software-Mittelwertbildung. Gleichzeitig dürfen Lüftungsöffnungen keine direkte Eintrittsstelle für Spritzwasser werden. Ein späterer Versuchsvergleich mit einem externen Referenzthermometer und einem unabhängigen Barometer ist sinnvoll.

**Bildhinweis D04 – Sensorbelüftung im Gehäusemodell:** `images/04_cad_sensor_vent.png`  
*Bildunterschrift: CAD-Entwurf mit Belüftungsgitter und internen Befestigungselementen. Die thermische Entkopplung des BME280 ist ein wesentlicher Punkt für die nächste Gehäuserevision.*

## 7. Bedienung: OLED, Taster, Licht und Signale

Die Benutzeroberfläche ist auf die begrenzte Fläche von **128 × 64 Pixeln** abgestimmt. Im Hauptmenü sind die Seiten **Status, GPS, Wetter, Logging, Tracks, Anker, Licht, Settings und System** vorgesehen. Vier Taster übernehmen die Navigation. Beim normalen Blättern wechseln Hoch und Runter die Seite, OK öffnet die jeweilige Funktion, und Zurück führt zur vorherigen Ansicht beziehungsweise Statusseite. Kritische Aktionen wie Trackstopp, Neustart und Herunterfahren sind mit einer Bestätigung versehen.

Im Einstellungsmenü lassen sich unter anderem Tastentöne und Signale, der Display-Timeout, die Bildinvertierung, der Kontrast und der LED-Herzschlag verändern. Das Display kann nach einer festgelegten Inaktivitätszeit schlafen gehen. Der erste Tastendruck nach dem Ruhezustand weckt zunächst nur die Anzeige, ohne gleichzeitig eine Menüaktion auszulösen – ein kleines, aber wichtiges Detail zur Vermeidung unbeabsichtigter Eingaben.

Eine RGB-LED vermittelt Systemzustände und kann zusätzlich als einfache **Taschenlampe** verwendet werden. Die entsprechende Seite erlaubt die Wahl zwischen weißem Licht, etwa zur Orientierung in der Kajüte, und rotem Licht, das nachts wegen seiner gewöhnlich geringeren Blendwirkung attraktiv ist. Dabei gilt: Eine gewöhnliche RGB-Status-LED ist kein Ersatz für eine leistungsfähige Arbeitsleuchte; Helligkeit und Farbqualität sind von den verbauten Bauteilen abhängig.

Die akustische Rückmeldung erfolgt über einen passiven Summer. Kurze Muster unterscheiden Tasteneingaben, Marker, Trackstart und Trackende von Warnungen und Alarmen. Wichtig ist die implementierte Prioritätslogik: Eine ausgelöste Ankerwarnung beziehungsweise ein Ankeralarm soll nicht durch den Taschenlampenmodus überdeckt werden. Gerade bei einem Gerät mit mehreren Funktionen ist diese Priorisierung sicherheitsrelevanter als die bloße Zahl der verfügbaren Anzeigen.

Die mechanische Bedienung ist noch nicht abgeschlossen. Die Position und Zugänglichkeit der Taster im gegenwärtigen Gehäuseentwurf gehören ausdrücklich zu den offenen Problemen. Auch ist zu entscheiden, ob eine zukünftige Variante weniger Taster und stattdessen eine lokale Weboberfläche verwenden soll. Ein **hybrider Ansatz** ist aus heutiger Sicht plausibel: zuverlässiges autonomes Logging, wenige robuste Bedienelemente am Gehäuse und komfortable Konfiguration beziehungsweise Datenübertragung über das Smartphone.

## 8. GPS-basierte Ankerwache – Funktionsprinzip und Grenzen

Die Ankerwache ist eine der anspruchsvolleren SailSense-Funktionen, weil sie nicht nur Daten darstellt, sondern aus ihnen Handlungsbedarf ableiten soll. Ihr Konzept orientiert sich am **Ankerabwurfpunkt** als Ausgangspunkt. Nach dem Setzen dieses Punkts kann das Boot zurücktreiben und der Abstand bei belasteter Kette als Radius festgelegt werden. Alternativ lassen sich Radius und ein zusätzlicher Sicherheitsbereich am Gerät verändern.

Der aktuelle Code unterscheidet mehrere Zonen: Innerhalb des gewählten Radius bleibt die Anzeige unauffällig. Ab einem definierten Anteil des Radius (standardmäßig **90 Prozent**) beginnt eine optische Vorwarnung. Erreicht die Position den eigentlichen Radius, folgt eine deutlichere optische Gefahranzeige. Erst außerhalb von **Radius plus Puffer** wird ein akustischer Alarm vorbereitet; in der vorliegenden Konfiguration muss die Überschreitung mindestens **acht Sekunden** anhalten und an mindestens **drei** aufeinanderfolgenden gültigen Punkten festgestellt werden. Ein wiederholtes akustisches Signal und eine auffällige rot-blaue Lichtfolge kennzeichnen den Alarmzustand.

Diese Verzögerungen sollen nicht jeden GPS-Ausreißer zu einem schrillen Weckruf machen. Allerdings kann der verwendete Mittelpunkt nur näherungsweise dem tatsächlichen Ankerstandort entsprechen, und der GPS-Empfänger misst die Position des Geräts – nicht die des Ankers. Schwojen, Strömung, Winddrehung, Kettenlänge, Rumpfgeometrie und GPS-Ungenauigkeit müssen daher berücksichtigt werden. Ein ausgereiftes System müsste zusätzlich **GPS-Ausfall und veraltete Fixes eigenständig alarmieren**, die Alarmfunktion bei Fehlern bevorzugt sicher gestalten und das Verhalten in realen Ankersituationen systematisch testen.

**SailSense ist gegenwärtig keine zertifizierte Sicherheits- oder Navigationsanlage. Die Ankerwache darf nicht als alleinige Überwachung eines ankernden Boots verwendet werden.** Dieser Hinweis ist nicht bloße Vorsichtssprache, sondern eine unmittelbare Folge des Prototypenstatus und der bekannten Grenzen satellitengestützter Positionsmessung.

## 9. Energieversorgung und Langzeitbetrieb

Die Versorgung des Raspberry Pi und der Peripherie erfolgt im Prototyp über USB. Ein Messfoto zeigt ungefähr **4,992 V**, **0,160 A** und damit **0,802 W** zum Zeitpunkt der Aufnahme. Die Werte demonstrieren die Größenordnung einer konkreten Betriebssituation; sie sind jedoch weder ein spezifizierter Maximalverbrauch noch ein normierter Langzeitdurchschnitt. Der Verbrauch hängt insbesondere von GPS-Empfänger, Displayzustand, WLAN-Aktivität, LED-Helligkeit, Prozessorlast und angeschlossener Peripherie ab.

Für einen mehrtägigen Törn ist daher nicht nur die Nennkapazität einer Powerbank entscheidend. Es zählen deren tatsächlich nutzbare Energie in Wh, Wandlungsverluste, Eigenverbrauch und das Verhalten bei kleiner Last. Auch kurzzeitige Spannungseinbrüche und schlecht sitzende USB-Stecker können einen Raspberry Pi unerwartet zurücksetzen. Ein vorgeschalteter Wandler, ein ausreichend dimensionierter Puffer oder eine geeignete USV-Lösung könnten später mehr bewirken als eine rein softwareseitige Optimierung.

In der vorliegenden Software sind bereits einige Sparansätze enthalten: Die Sensorabfrage erfolgt periodisch statt permanent, das OLED kann automatisch abgeschaltet werden und der LED-Herzschlag ist konfigurierbar. Potenzial bieten eine gezielte Reduktion der Anzeigeaktivität, eine Messung einzelner Verbraucher, die Prüfung des WLAN-Betriebs und ein durchdachtes Verhältnis von GPS-Abtastrate zu gewünschter Datenqualität. Die Aufgabe lautet ausdrücklich nicht, maximale Laufzeit um jeden Preis zu erreichen, sondern **ausreichende Datenqualität bei kalkulierbarer Energieaufnahme** zu sichern.

Vor einer Langzeitfreigabe sind Messreihen mit definierter Versorgung und dokumentierten Betriebsmodi nötig, beispielsweise: Leerlauf ohne Track, aktive Aufzeichnung, OLED eingeschaltet und ausgeschaltet, Alarm und maximal helles LED-Licht. Ergänzend sollte ein Stromausfalltest zeigen, ob die Dateien danach noch lesbar sind.

**Bildhinweis D05 – Leistungsaufnahme:** `images/05_usb_power_measurement.jpg`  
*Bildunterschrift: USB-Messung während eines Versuchs: rund 4,99 V und 0,16 A, entsprechend etwa 0,8 W. Der Momentanwert ist keine allgemeine Laufzeitgarantie.*

**Bildhinweis D06 – längerer Testbetrieb:** `images/06_usb_long_run.jpg`  
*Bildunterschrift: USB-Messgerät während eines länger dauernden Versuchs. Angezeigte Summenwerte hängen vom Messgerät, dessen Messbereich und dem jeweiligen Aufzeichnungszeitraum ab.*

## 10. Entwicklung des 3D-gedruckten Gehäuses

Ein funktionsfähiger Breadboard-Aufbau beweist zunächst nur die elektrische und softwareseitige Machbarkeit. Für den Einsatz an Bord müssen die Komponenten mechanisch zusammenfinden. Deshalb entsteht für SailSense ein **eigenes Gehäusemodell in Autodesk Fusion**, das anschließend im **3MF-Format** für die Druckvorbereitung bereitgestellt wurde. Die beigefügten CAD-Ansichten zeigen ein mehrteiliges, kastenförmiges Gehäuse mit internen Stützen, Befestigungspunkten, Öffnungen für Bedienelemente und Luftdurchlässen.

Der Entwurf versucht mehrere Anforderungen gleichzeitig zu erfüllen: Eine möglichst kompakte Anordnung, Zugang zu Anschlüssen, sichere Befestigung von Platine und Peripherie, reproduzierbare Montage und ausreichende Belüftung des Sensors. Die sichtbaren Bohrungen und Ausnehmungen sind dabei nicht nur gestalterische Elemente. Sie definieren die späteren Montagewege, Einbautoleranzen und die Zugänglichkeit der Funktionen.

Besonderen Verbesserungsbedarf gibt es bei **den Positionen der Taster** und **der Gitterhalterung für den BME280**. Die derzeitigen Positionen sollten vor dem nächsten Druck anhand realer Abmessungen der Schalter und ihrer Betätigungswege überarbeitet werden. Die Sensorhalterung muss einerseits genügend Frischluft zulassen, andererseits Kabel, Verschraubungen und die Wärmeabstrahlung des Raspberry Pi berücksichtigen. Eine separate, thermisch entkoppelte Sensorkammer wäre eine mögliche Weiterentwicklung.

Auch eine gute CAD-Konstruktion ist erst nach gedruckter Montage wirklich beurteilt. Zu prüfen sind die Passungen der Schraubdome, Wandstärken, Einschraubrichtungen, Bruchfestigkeit von Stegen, Montagereihenfolge, Kabelbiegeradien und die Zugentlastung an USB- und Stromanschlüssen. Ein Gehäuse mit Luftschlitzen ist **nicht wasserdicht**. Für den Bootseinsatz braucht es mindestens ein klares Schutzkonzept gegen Spritzwasser, Kondenswasser und Salzablagerungen. Ein geeigneter Montageplatz unter Deck kann das Risiko reduzieren, beseitigt es aber nicht.

Die 3D-Daten werden auf GitHub veröffentlicht: Die **`.f3d`-Datei** dient als bearbeitbares Fusion-Konstruktionsmodell, die **`.3mf`-Datei** enthält das 3D-Modell in einem verbreiteten Austauschformat. Die Unterstützung einzelner 3MF-Metadaten hängt vom eingesetzten Slicer ab. Ergänzende STL- oder STEP-Exporte wären für die plattformübergreifende Weiterverwendung sinnvoll, sind aber im bereitgestellten Material nicht enthalten. Für das Modell sollten außerdem Versionsnummern, Druckorientierung, Materialwahl, Schrauben und eine Stückliste dokumentiert werden.

**Bildhinweis D07 – Fusion-Modell:** `images/07_fusion_enclosure.png`  
*Bildunterschrift: Explosionsähnliche CAD-Ansicht des SailSense-Gehäuses mit internen Befestigungen, Tasteröffnungen und Sensorbelüftung. Der Aufbau befindet sich in konstruktiver Überarbeitung.*

**Bildhinweis D08 – Druckvorbereitung:** `images/08_bambu_print_layout.png`  
*Bildunterschrift: Anordnung der Gehäuseteile auf dem virtuellen Druckbett in Bambu Studio. Die Veröffentlichung des 3MF-Modells ermöglicht eigene Druckversuche und konstruktive Anpassungen.*

## 11. Dateien, Datensicherung und Reproduzierbarkeit

SailSense verfolgt bewusst einen transparenten Dateiansatz. Die Konfiguration steht unter `config/settings.yaml`. GPS-Tracks werden im aktuellen Beispiel unter `/home/user/sailsense/logs/tracks/` abgelegt, der Trackindex unter `logs/tracks/tracks_index.csv`; GPX-Dateien entstehen unter `data/exports/`. Wetterdaten werden unter `logs/weather/` abgelegt. Die Datenpfade sind im Programm gegenwärtig an das Beispielverzeichnis `/home/user/sailsense` gekoppelt. Eine vollständig portable Installation sollte diese Annahmen später durch zentral konfigurierbare Projekt- und Datenverzeichnisse ersetzen.

Neben der Vollanwendung enthält das ZIP mehrere Diagnose- und Testskripte sowie ältere Entwicklungsstände. Sie sind für die Nachvollziehbarkeit hilfreich, sollten im öffentlichen Repository jedoch klar von produktivem Code getrennt werden. Insbesondere fehlen im bereitgestellten Projektstand eine formalisierte Abhängigkeitsdatei und ein vollständiges automatisiertes Installationsverfahren. Die Software benötigt unter anderem `PyYAML`, `pyserial`, `pynmea2`, `gpiozero`, `Pillow` und die passenden Adafruit-Bibliotheken für OLED, Blinka und BME280. Hardwarebibliotheken sollten auf der Zielplattform getestet und mit konkreten Versionsanforderungen dokumentiert werden.

Der reguläre Start ist im ZIP über `scripts/run_app.sh` auf `PYTHONPATH=src python -m sailsense.app` ausgelegt. Für den praktischen Dauerbetrieb sollte der systemd-Dienst Logausgaben in das Journal schreiben, nach nachvollziehbarer Fehlerstrategie neu starten und sauber auf das Beenden reagieren. Der derzeitige Systemmenü-Code erwartet außerdem ein privilegiertes Hilfsprogramm unter `/usr/local/sbin/sailsense-power`, das gesondert installiert und mit minimal nötigen Rechten konfiguriert werden muss.

Die Datensicherung ist besonders wichtig, weil viele Windows-Systeme die Linux-Partition einer Raspberry-Pi-SD-Karte nicht ohne Zusatzsoftware lesen können. Geplant ist daher ein einfacher Dateidownload über ein lokales Netzwerk beziehungsweise eine Weboberfläche. Solange dies nicht integriert ist, erfolgen Wartung und Datentransfer typischerweise per SSH/SCP. Eine spätere Weblösung sollte ausdrücklich sowohl **Dateiexport** als auch **Gerätestatus** abdecken, ohne die Kernaufzeichnung von einer aktiven WLAN-Verbindung abhängig zu machen.

## 12. Offene Probleme, Prioritäten und nächste Schritte

Der vorliegende Stand ist ein funktionsreicher Prototyp. Einige Schwächen betreffen hauptsächlich Komfort und Konstruktion, andere unmittelbar den Schutz aufgezeichneter Daten oder die Zuverlässigkeit von Warnfunktionen. Für die weitere Entwicklung empfiehlt sich folgende Reihenfolge:

**Priorität A – Zuverlässigkeit und Datensicherheit.** Die Anwendung muss nach einem Neustart verlässlich wieder hochfahren; unterbrochene Tracks sollen erkannt, indiziert und nachträglich exportiert werden können. GPS-Portwechsel, vorübergehender Empfangsverlust und wiederkehrender Empfang müssen ohne manuelle Eingriffe behandelt werden. Fehler im I²C-Bus dürfen möglichst nicht die gesamte Aufzeichnung beenden. Ein Verlust gültiger GPS-Daten muss in der Ankerwache ausdrücklich als Fehlerzustand erkennbar und alarmierbar sein. Ergänzend braucht es reproduzierbare Installation, ein Versionsschema, Tests und gesicherte Standardkonfigurationen.

**Priorität B – Gehäuse und praktische Ergonomie.** Die Positionen der vier Taster werden neu konstruiert, der BME280 bekommt eine mechanisch und messtechnisch bessere Halterung. Ein- und Ausgänge, Kabelwege, Zugentlastung, Befestigungspunkte und Montagefolge sind im CAD zu überprüfen. Nach dem Druck folgen Passungsversuche und ein realistischer Feuchte- und Temperaturtest. Die Konstruktion sollte nachvollziehbar versioniert werden, statt ältere Dateien ohne Änderungsprotokoll zu überschreiben.

**Priorität C – Energieoptimierung.** Ein sauberes Verbrauchsprofil soll den Grundverbrauch und den Anteil einzelner Verbraucher quantifizieren. Darauf aufbauend lassen sich Display-Timeout, LED-Betrieb, WLAN und Abtastraten zielgerichtet optimieren. Denkbar sind zusätzliche Batterieinformationen und eine Warnung bei Unterspannung, sofern die dafür erforderliche Messhardware vorgesehen wird. Die Wirksamkeit ist jeweils in Wh und nicht nur anhand der Nenn-mAh einer Powerbank zu bewerten.

**Priorität D – Weboberfläche.** Ein lokal erreichbarer Webserver soll live GPS-, Wetter- und Statusdaten anzeigen, Konfigurationswerte bearbeiten und Tracks beziehungsweise Wetterdaten herunterladen können. Besonders reizvoll wäre eine browserbasierte, responsive Oberfläche, die auf dem Smartphone ohne eigene App funktioniert. Eine spätere WLAN-Access-Point-Funktion könnte die Nutzung ohne vorhandenes Bordnetz ermöglichen. Authentifizierung, Netzwerksicherheit, gleichzeitige Zugriffe und der sparsame Umgang mit Energie gehören von Beginn an zur Planung. Kritische Funktionen, insbesondere die Ankerwache, dürfen bei Ausfall der Webverbindung nicht ausfallen.

**Priorität E – MPU/IMU und zusätzliche Daten.** Die vorbereitete IMU-Schnittstelle könnte später Roll-, Nick- und Bewegungsdaten liefern. Dafür müssen Sensorvariante, Achsorientierung, Einbaulage, Abtastrate, Kalibrierung und Datenfilterung geklärt werden. Aus einer MPU allein folgt weder eine verlässliche Windmessung noch eine vollständige Segel-Leistungsanalyse. Erst in Verbindung mit geeigneten zusätzlichen Sensoren und einer sauberen Datenmodellierung entstehen belastbare neue Funktionen.

Weitere sinnvolle Arbeiten sind eine Echtzeituhr für robuste Zeitstempel ohne GPS-Fix, UTC-/Zeitzonendarstellung, Logging-Rotation und Speicherkapazitätsüberwachung, ein watchdoggestützter Wiederanlauf, ein sicherer Umgang mit `SIGTERM`, ein versioniertes Verdrahtungsdiagramm, reproduzierbare Sensortests, Datenqualitätskennzeichnungen und der Vergleich von Trackdistanz mit einer unabhängigen Referenz.

## 13. Ausblick und Einordnung

SailSense zeigt, wie aus einer scheinbar kleinen Idee ein System mit zahlreichen disziplinübergreifenden Fragen entsteht. Ein GPS-Punkt muss geprüft, ein Sensorwert zeitlich eingeordnet, eine Kurve sinnvoll skaliert, ein Alarm zuverlässig ausgelöst und ein Gehäuse auch nach dem hundertsten Tastendruck noch bedienbar sein. Der eigentliche Erkenntnisgewinn liegt deshalb nicht allein in einer Reihe funktionierender Module, sondern in ihrer Integration.

Die nächsten Schritte führen von einem funktionalen Elektronik- und Softwareprototyp zu einem **robusten Bordgerät**: nachvollziehbar dokumentiert, wartbar, mit verlässlicher Datensicherung und einer Gehäusekonstruktion, die sich tatsächlich drucken und montieren lässt. Ob SailSense langfristig stärker als Displaygerät oder als vom Smartphone bedienter Headless-Logger konzipiert wird, bleibt bewusst offen. Die entscheidende Eigenschaft soll in beiden Varianten dieselbe sein: **Das Gerät arbeitet weiter, auch wenn niemand hinsieht.**

---
# PART II — ENGLISH

## 1. The idea behind SailSense

A sailing boat continuously produces information that is useful both during a passage and afterwards: the actual course sailed, distance travelled, changes in atmospheric pressure, and variations in temperature and humidity. Some of this information is available on chartplotters, smartphones or weather instruments, but it is often scattered across different devices and applications. **SailSense** was conceived as a way to bring several of these measurements together in one small, independent device.

SailSense is a Raspberry Pi–based monitoring and data-logging project designed with sailing in mind. It combines a GPS receiver for position and movement data, a Bosch BME280 environmental sensor, a compact OLED display and a straightforward physical user interface. Additional elements include visual and audible feedback, a GPS-based anchor watch, and the ability to export recorded routes as GPX files for further analysis.

The intention is deliberately **not** to replace a professional chartplotter or certified marine instrumentation. SailSense is an auxiliary device: part electronic logbook, part barograph, and part experimental platform for exploring how embedded computing, sensors and mechanical design can work together. One essential design goal is autonomous operation. Logging should continue in the background regardless of whether a phone, laptop or other display is connected.

The project is also a hands-on engineering exercise. Electronics, Python programming, measurement principles and CAD modelling all influence the final result. The photographs document an early stage with a Raspberry Pi, breadboard and exposed connections; the CAD files illustrate the subsequent attempt to turn that experimental setup into a self-contained instrument. This transition is important. A working circuit on a desk is only the first step toward a device that can be installed, operated, powered and protected aboard a boat.

**Figure E01 — Electronic prototype:** `images/01_prototype_breadboard.jpg`  
*Caption: Early SailSense prototype on a breadboard, combining the Raspberry Pi and peripheral wiring. The open setup simplifies experimentation and troubleshooting but is not yet suitable for permanent installation aboard a boat.*

## 2. Design goals and engineering approach

The project is guided by three complementary principles. The first is **transparent, reusable data**. Position records and environmental measurements are saved in readable CSV files, while completed GPS tracks can be exported to the widely supported GPX format. Data remains available for analysis without dependence on a proprietary cloud service or a specific mobile application.

The second principle is **practical interaction**. A 128 × 64-pixel display, four buttons, a multicolour LED and a small buzzer are sufficient to operate the principal functions: start or stop a track, insert a waypoint-style marker, inspect pressure trends, select settings and activate the anchor watch. Physical controls remain useful when a phone is inconvenient, particularly at night or when the user's hands are wet.

The third principle is **extensibility**. The software separates GPS handling, environmental monitoring, display logic, data storage and physical input/output into individual modules. This makes additions such as an inertial measurement unit, advanced energy management or a browser-based interface conceptually straightforward. Those additions, however, must be distinguished from capabilities that are already implemented in the supplied source snapshot.

These goals introduce genuine trade-offs. A permanently lit display improves immediate readability but consumes additional power. A sealed enclosure protects electronics from water but may trap heat around the temperature sensor. More frequent sampling captures detail at the expense of storage and energy. SailSense is being designed around these compromises rather than pretending that a single component or software setting can eliminate them.

## 3. Hardware and electronic architecture

The heart of the device is a **Raspberry Pi Zero 2 W**. Its compact size and moderate power requirements make it attractive for a portable instrument. It provides enough processing capacity to parse NMEA messages, read an I²C environmental sensor, update the OLED, operate the interface and write files to a microSD card. Integrated wireless networking also offers a potential foundation for a future local web interface.

The supplied prototype is organised around the following components:

| Component | Purpose | Interface / status |
|---|---|---|
| Raspberry Pi Zero 2 W | Processing, storage and application control | Present |
| USB GPS/GNSS receiver | Position, speed over ground, course and GPS time | USB serial; configured `/dev/ttyACM0`, 9600 baud |
| Bosch BME280 | Temperature, relative humidity and atmospheric pressure | I²C; configured address `0x76` |
| 128 × 64 OLED | Menus, live values, plots and track overview | I²C; configured address `0x3C` |
| Four push buttons | Up, down, select and back | BCM GPIO 17, 27, 22, 23 |
| RGB status LED | Device indications, warning patterns and illumination | BCM GPIO 5, 6, 13; common-anode configuration |
| Passive buzzer | Button feedback, notifications and alarm tones | BCM GPIO 12 |
| IMU / MPU module | Potential future motion and orientation data | Configuration placeholder only; **not yet integrated** |
| USB power supply | Powers the prototype | Tested experimentally; final power architecture pending |

The GPIO numbers refer to the **Broadcom numbering scheme**, not the physical pin positions on the 40-pin header. The attached `config/settings.yaml` is the authoritative source for the current prototype configuration. Raspberry Pi GPIO inputs operate at 3.3 V logic levels and are not 5 V tolerant; any external circuits must use appropriate voltage levels, resistors and protective components. A complete electrical schematic and a bill of materials remain to be documented separately.

The display and environmental sensor share the standard I²C bus, normally on SDA/GPIO 2 and SCL/GPIO 3. Although this reduces wiring complexity, it introduces a dependency on compatible sensor boards, correct addresses and suitable pull-ups. The project history includes OLED communication problems, illustrating why visually similar modules should not automatically be treated as electrically or logically interchangeable. The source archive therefore includes dedicated peripheral tests for incremental fault isolation.

**Figure E02 — Raspberry Pi wiring:** `images/02_raspberry_pi_wiring.jpg`  
*Caption: Raspberry Pi Zero 2 W connected to the prototype's GPIO wiring. Serial GPS, shared I²C peripherals and discrete inputs and outputs form the essential electrical architecture.*

**Figure E03 — OLED start-up screen:** `images/03_oled_startup.jpg`  
*Caption: The monochrome OLED during SailSense start-up. Local status feedback works without a conventional monitor or keyboard.*

## 4. Software structure and runtime operation

SailSense is primarily written in **Python**. Its code is arranged under `src/sailsense/`, with `sailsense.app` as the main interactive application. Smaller standalone programs and scripts are provided for logging experiments, display diagnostics and peripheral tests. Rather than treating each hardware device as a separate application, the main program combines them in a continuously executing event loop.

The source tree separates key responsibilities:

- `gps/` implements NMEA input, distance calculations and track-session management.
- `weather/` reads the BME280, aggregates measurements, stores history and restores saved samples.
- `display/` drives the OLED, renders environmental graphs and draws simplified track maps.
- `anchor/` contains the GPS-based anchor watch and its warning-state model.
- `input/` and `output/` manage buttons, the RGB LED and the buzzer.
- `storage/` and `export/` handle CSV files, the track index and GPX export.
- `runtime_settings.py` connects on-device settings with persistent YAML configuration.
- `system/` provides entry points for privileged shutdown and reboot actions.
- `imu/` is currently only a placeholder for a possible future sensor integration.

On start-up, the program loads its settings, initialises the connected devices, restores recent weather measurements and reads the list of completed tracks. It then polls the GPS and the weather service, updates the track manager, processes anchor-watch events, refreshes the OLED and controls LED or buzzer feedback. The sampling intervals for GPS tracking and weather storage are handled separately; the display does not need to refresh whenever a new data row is written.

The intended deployment model is a **systemd service** on the Raspberry Pi. This allows SailSense to start automatically after boot without a monitor or keyboard. The archive provides shell launch scripts, but it does not yet constitute a complete, reproducible installer with packaged dependencies and a ready-to-deploy service definition. That distinction matters for anybody attempting to build a second device from the published project.

The uploaded Python source passes a static syntax compilation check. This does not validate the physical circuit, confirm every dependency on Raspberry Pi OS or establish reliable unattended performance. Hardware-in-the-loop tests and a documented acceptance procedure remain necessary.

## 5. GPS logging and the electronic voyage record

The GPS reader consumes NMEA data from the receiver's serial interface. It uses **GGA sentences** to obtain supplemental fix information such as satellite count, altitude, fix quality and horizontal dilution of precision (HDOP). Valid **RMC sentences** supply UTC time, latitude, longitude, speed over ground and course over ground. Invalid RMC status messages do not become recorded positions.

Tracking is session-based. A user starts recording from the device interface, and the program opens a dedicated CSV file for that journey. The current configuration limits writing to approximately **one accepted point every five seconds**. A simple quality filter requires at least **five satellites** and rejects points with an HDOP above **5.0**, when HDOP is available. A jump exceeding **500 metres** relative to the previous accepted point is also discarded. These measures reduce some obvious anomalies; they should not be mistaken for a complete statistical position filter or an assurance of navigational accuracy.

Distances between accepted positions are calculated using the **Haversine formula**. The program accumulates metres internally and converts the result into nautical miles for the nautical display, using **1 nautical mile = 1,852 metres**. During recording, the OLED shows elapsed time, distance and the number of accepted points. The user can also insert a marker to identify an event or location of interest within the track data.

When a track is stopped normally, SailSense writes a summary row to its track index and automatically attempts to export the corresponding CSV file to **GPX 1.1**. Standard GPX elements describe the recorded positions, timestamps and other supported attributes. Additional SailSense data—including speed, course, segment distance, accumulated distance, fix quality and markers—are stored as namespaced XML extensions. Some third-party GPX applications will ignore these extensions, but the underlying track remains accessible.

The OLED interface also allows browsing previously completed tracks and displaying a compact, north-up representation of the selected track. This is a deliberately simplified graphic rather than a chart with coastlines, hazards or navigation marks. It is useful for quick review, **not** for safe navigation.

An important limitation emerges from the implementation: a track is fully added to the index only after the normal stop procedure. In the event of an abrupt loss of power, previously flushed CSV rows may still exist, but the track might not appear in the index or receive an automatic GPX export. Detecting and recovering interrupted sessions is therefore a high-priority improvement.

## 6. Environmental monitoring and the barograph

The **Bosch BME280** measures three atmospheric variables: **temperature (°C)**, **relative humidity (%)** and **pressure (hPa)**. SailSense deliberately separates fast sensor acquisition from slower display aggregation and long-term storage. This makes short-term readings available without producing unnecessarily large historical logs.

The current settings specify a sensor read approximately every **10 seconds**. The displayed values are averaged across a rolling window of roughly **60 seconds**, while long-term measurements are normally recorded as a mean value every **15 minutes**. A history buffer of **96 samples** represents about **24 hours** at that recording interval. Previously stored measurements can be reloaded after the application restarts. The `SAILSENSE_WEATHER_STORAGE_INTERVAL` environment variable can temporarily override the persistence interval in seconds for experiments and diagnostics.

The pressure chart provides a compact visual history on the 128 × 64 OLED. Similar graph screens are available for temperature and humidity. A particularly useful feature is the configurable **barograph reference line**. In automatic mode, the centre line is based on the mean of the visible pressure readings. In manual mode, the user can set a fixed reference—for example, **1013 hPa**—so that deviations above and below that value are immediately apparent. The vertical scale is independently adjustable in **hPa per pixel**, with a value such as **0.25 hPa/pixel** displayed explicitly. Several predefined zoom levels are supported.

The result is more informative than an automatically rescaled graph that changes its appearance without telling the user why. A fixed reference and an explicit scale make it easier to compare changes over time. Nevertheless, the instrument does **not** provide a standalone weather forecast. Pressure tendencies must be interpreted alongside local conditions, synoptic weather information and the specific sailing area.

The sensor's physical location is just as important as the aggregation algorithm. A BME280 mounted close to the processor inside a poorly ventilated enclosure may read artificially high temperatures; because relative humidity depends on temperature, humidity readings may also become biased. The enclosure's proposed ventilation grille and separate sensor mounting are therefore integral to the measurement concept. They must permit suitable airflow while limiting exposure to spray and condensation. A comparative measurement against independent instruments is a necessary next step before making accuracy claims.

**Figure E04 — Sensor ventilation:** `images/04_cad_sensor_vent.png`  
*Caption: CAD view showing a ventilation opening and internal mounting features. Mechanical placement and thermal isolation of the BME280 are important objectives for the next enclosure revision.*

## 7. User interface, lighting and feedback

The interface is designed around the limited space of a **128 × 64-pixel OLED**. The main pages in the current application are **Status, GPS, Weather, Logging, Tracks, Anchor, Light, Settings and System**. Four physical buttons support navigation and selection. Up and Down move between pages or options, OK selects the current action and Back returns to the previous view. Potentially disruptive operations, including stopping a track and restarting or shutting down the system, require a confirmation step.

Runtime settings include button clicks and other audible signals, display timeout, display inversion, contrast and the LED heartbeat. The OLED can turn off after a period of inactivity. Importantly, the first button press while the display is asleep only wakes the screen; it is not immediately treated as a navigation or confirmation command. This reduces the risk of accidental operations.

The RGB LED provides status feedback and also supports a basic **flashlight mode**. Users can switch between white light for finding objects and red light for less intrusive illumination at night. The software drives the selected channels at their configured maximum for that mode. The practical light output, however, depends on the LED, resistors and enclosure design. A small RGB status LED is not equivalent to a dedicated marine work light.

A passive buzzer produces different patterns for button feedback, markers, track start/stop, warnings and alarms. The implementation also includes a priority rule: warnings from the anchor-watch function must not be hidden by the flashlight. Such decisions are crucial in a multifunctional device, where a convenient secondary mode must not interfere with a more important alert.

The physical interface is not yet finalised. The **button positions** visible in the current enclosure concept require redesign for comfortable and reliable operation. One future option is a fully headless device controlled from a smartphone through a local web server. A **hybrid approach** offers a strong compromise: logging and critical monitoring remain independent; basic actions stay available on physical controls, while advanced settings, graphs and file downloads are handled through the browser.

## 8. GPS-based anchor watch: operation and limitations

The anchor-watch feature is among the more demanding elements because it must interpret incoming data and decide when to alert the crew. Its geometry begins with an **anchor drop position**. After this position has been recorded, the vessel may drift back until the anchor rode is under tension, allowing the user to set a radius from the measured position. The radius and an additional buffer can also be adjusted manually through the interface.

The current implementation distinguishes several states. Within the selected radius, no major warning is indicated. At a specified fraction of that radius—**90% by default**—the LED begins an optical pre-warning. Crossing the configured radius triggers a more prominent danger indication. The audible alarm is associated with the larger boundary defined by **radius plus buffer**. In the supplied settings, the receiver must report a position beyond that boundary for at least **eight seconds** and on at least **three qualifying observations** before the alarm starts. The alarm then produces repeated sound signals and an alternating red/blue visual pattern.

This combination of thresholds, points and time is intended to reduce nuisance alarms caused by individual GPS errors. It is not a guarantee of safe anchor holding. The recorded position describes the GPS receiver, not the anchor itself; the boat may move through a legitimate swinging circle as wind or current changes. Chain geometry, the location of the drop point, receiver accuracy, multipath and transient loss of fixes all affect the result.

The current code also needs a robust and independently detectable **loss-of-GPS alarm**. Without a fresh, valid position, the system may be unable to establish that the boat has moved outside its configured radius. Additional failure-state handling, long-duration trials and controlled alarm tests are therefore essential.

**SailSense is an experimental auxiliary system, not a certified navigation or safety device. Its anchor watch must never be relied upon as the sole method of monitoring an anchored vessel.** That limitation follows directly from the prototype's unverified failure modes and the intrinsic uncertainty of GPS positioning.

## 9. Power supply, consumption and long-term operation

The prototype is powered through USB. One supplied photograph of a USB meter shows approximately **4.992 V** at **0.160 A**, corresponding to about **0.802 W** at that moment. This illustrates the approximate magnitude of consumption in one operating condition, but it is not a calibrated maximum, a representative daily average or a guaranteed figure for every hardware configuration. Power demand changes with GPS receiver activity, display brightness, wireless networking, LED output, CPU load and peripheral behaviour.

For multi-day use, the nominal mAh rating of a power bank is only part of the equation. The relevant quantity is usable energy in **watt-hours**, after accounting for conversion losses, the power bank's own consumption and its behaviour at low loads. Short voltage dips or unreliable USB connections can also reboot the Raspberry Pi. A future power architecture may benefit from a high-quality regulated supply, suitable buffering or an appropriate UPS module.

Several energy-saving mechanisms are already available in software. Sensor acquisition is periodic, the display can sleep automatically, and LED heartbeat signalling is configurable. Further options include optimising the display refresh policy, benchmarking each peripheral separately, reducing unnecessary wireless activity and balancing track resolution against the intended analysis. Energy optimisation should be measured rather than guessed: a longer runtime is only useful if adequate GPS and environmental data are preserved.

Before treating SailSense as ready for an extended passage, the power budget should be measured under defined conditions: idle operation, active tracking, OLED on and off, alarm signalling, flashlight at full brightness and any proposed wireless mode. Sudden-disconnect experiments should also establish what happens to the files when the supply disappears unexpectedly.

**Figure E05 — Power measurement:** `images/05_usb_power_measurement.jpg`  
*Caption: USB meter showing approximately 4.99 V and 0.16 A during a prototype test, equivalent to about 0.8 W. This is an instantaneous observation, not a rated power specification.*

**Figure E06 — Extended bench test:** `images/06_usb_long_run.jpg`  
*Caption: A USB meter used during an extended test. Cumulative energy and duration readings depend on the meter and the actual measurement period.*

## 10. Designing the 3D-printed enclosure

An exposed breadboard is ideal for experiments but unsuitable for sustained use aboard a boat. The next stage of SailSense therefore involves a **custom enclosure designed in Autodesk Fusion** and prepared as a **3MF model** for 3D-printing workflows. The supplied CAD views show a multipart rectangular housing with internal mounting points, brackets, ventilation features and openings for buttons and connections.

The enclosure is not simply a cosmetic shell. It must keep the electronics mechanically secure while allowing access to controls, connectors and maintenance points. The internal standoffs, holes and support features dictate the order of assembly, the required fasteners and the clearance available for wires. The design also needs to balance compactness with serviceability: a component should be removable without damaging an adjacent part or tearing out a cable.

Two clear areas for revision have already been identified. First, the **button placement** needs improvement, based on actual switch dimensions, actuation travel and fingertip access. Second, the **BME280 grille and mounting arrangement** need rethinking so that the sensor can receive ambient air without being heated by the Raspberry Pi or exposed directly to splash water. A separate thermally isolated sensor pocket is a possible design direction.

The CAD model should also be checked for realistic printing and assembly tolerances, wall thickness, screw bosses, strain relief, connector clearance, cable bend radii, and a suitable mounting system for use below deck. Thermal management must not be confused with waterproofing. An enclosure with ventilation slots is **not watertight**; condensation and salt contamination still need to be considered. Selection of a protected installation location is therefore part of the design specification.

The original 3D design files are intended for publication on GitHub. The **`.f3d` file** preserves an editable Autodesk Fusion design, while the **`.3mf` file** provides a widely used 3D model container. The degree to which slicer-specific information is preserved varies between programs. Additional STL or STEP exports would improve portability but are not included in the submitted set. Future releases should state the enclosure revision, print orientation, recommended material, hardware and assembly instructions so that others can reproduce the build without guesswork.

**Figure E07 — Fusion enclosure design:** `images/07_fusion_enclosure.png`  
*Caption: CAD view of the multipart SailSense housing, showing internal supports, control openings and ventilation features. The design remains a prototype awaiting mechanical refinement.*

**Figure E08 — Print-bed arrangement:** `images/08_bambu_print_layout.png`  
*Caption: SailSense enclosure parts positioned in Bambu Studio. Publishing the 3MF model will allow others to inspect, print and refine the mechanical design.*

## 11. Data management, installation and maintainability

A deliberate advantage of SailSense is that recorded information remains in ordinary files. Runtime configuration is held in `config/settings.yaml`. With the paths provided in the current snapshot, GPS sessions are stored below `/home/user/sailsense/logs/tracks/`, the index at `logs/tracks/tracks_index.csv`, exported GPX files at `data/exports/`, and environmental measurements below `logs/weather/`. Several paths currently assume installation in `/home/user/sailsense`, and a more portable release should consolidate these into centrally configurable locations.

The source archive includes a substantial number of diagnostics, test utilities and historical code copies. These provide insight into the development process, but production files and obsolete versions should be separated clearly in a public repository. The supplied archive does not contain a complete dependency manifest or a turnkey installation procedure. Required Python packages include, among others, `PyYAML`, `pyserial`, `pynmea2`, `gpiozero`, `Pillow` and the appropriate Adafruit display, Blinka and BME280 libraries. Their versions and target operating system compatibility should be verified on a Raspberry Pi rather than inferred from package names alone.

The included `scripts/run_app.sh` starts the application by activating a virtual environment and invoking `PYTHONPATH=src python -m sailsense.app`. A future reproducible distribution should define that environment, provide a sample systemd unit, document permissions for the GPS serial device and specify the required I²C configuration. The System menu also expects a privileged helper at `/usr/local/sbin/sailsense-power` for controlled shutdown and reboot. This helper is not supplied as a complete installer in the archive and must be deployed with appropriately restricted privileges.

Backups deserve particular attention. Windows normally cannot browse the Linux filesystem on a Raspberry Pi microSD card without additional tools, so removing the card is not necessarily a practical data-retrieval strategy. Until a local web interface exists, files can be transferred using SSH and SCP. The proposed web server should ultimately offer clear access to **live status, recorded tracks, weather logs and configuration**, without ever making background logging depend on the presence of a phone or Wi-Fi client.

## 12. Known issues, development priorities and roadmap

The supplied snapshot already contains substantial functionality, but it remains a prototype. Some shortcomings affect usability; others concern data integrity or the reliability of functions that may be interpreted as safety warnings. For continued development, priorities should follow the severity of their consequences.

**Priority A — Reliability and data integrity.** Provide predictable startup and recovery, identify and repair interrupted track sessions, and allow delayed GPX export where required. Handle USB serial device renumbering, GPS loss and reconnection, and I²C errors without losing the entire recording session whenever possible. Make stale or missing GPS data an explicit fault condition for the anchor watch. Introduce automated tests, a reproducible installation process, versioned configurations and reliable error reporting.

**Priority B — Enclosure and ergonomics.** Redesign the positions of the physical buttons and the BME280 mounting and grille. Verify hardware clearances, cable routing, connector protection, strain relief and assembly order. Follow CAD revisions with actual test prints, fitting trials and environmental measurements. Track enclosure versions and changes alongside source-code revisions rather than replacing files without a history.

**Priority C — Power optimisation.** Measure a baseline power budget and the contribution of each peripheral before tuning. Investigate display duty cycle, LED signalling, wireless activity and GPS sampling rates. If suitable hardware is added, expose supply-voltage or battery-state information and detect undervoltage. Compare results in watt-hours, not only nominal power-bank milliamp-hours.

**Priority D — Local web interface.** Build a responsive browser interface for live GPS and weather information, graphs, configuration and track downloads. A Raspberry Pi–hosted access point could ultimately support phone access without an existing onboard Wi-Fi network. Security, authentication, concurrent interactions and energy consumption must be designed in from the start. Logging and alerting must continue even if the web server or client connection fails.

**Priority E — IMU integration and future sensors.** Define the intended MPU/IMU model, coordinate system, mounting orientation, sampling, calibration and filtering. Roll, pitch or motion measurements could enrich the dataset, but meaningful interpretation depends on accurate installation and calibration. An IMU alone cannot measure true wind, calculate sail trim performance or replace dedicated marine sensors.

Additional worthwhile improvements include an independent real-time clock for meaningful timestamps without a GPS fix, explicit UTC/local-time handling, disk-space warnings, log rotation, watchdog-based restart policies, clean shutdown handling on service termination, an electrical schematic, repeatable hardware test procedures and comparisons against reference instruments.

## 13. Conclusion and outlook

SailSense illustrates how quickly a seemingly simple logging idea becomes a multidisciplinary engineering project. A GPS point must be validated, environmental measurements must be aggregated intelligently, a graph needs a meaningful scale, an alarm must fail predictably, and a housing must remain usable and maintainable beyond a single successful bench test. The real challenge is not creating isolated features but making them work together consistently.

The next step is to transform the current electronics and software prototype into a **robust, reproducible auxiliary instrument for sailing**: documented, serviceable, data-safe and housed in a practical printed enclosure. The final balance between a local display and a smartphone-controlled headless design remains open. In either approach, the essential principle should remain unchanged: **SailSense keeps measuring even when nobody is watching.**

---

# APPENDIX / ANHANG — PHOTO PLAN AND REPOSITORY STRUCTURE

## A. Suggested photo sequence / Empfohlene Bildfolge

| Figure | Source file in this package | Recommended placement |
|---|---|---|
| 01 | `images/01_prototype_breadboard.jpg` | Project introduction / Projektvorstellung |
| 02 | `images/02_raspberry_pi_wiring.jpg` | Hardware and wiring / Hardware und Verdrahtung |
| 03 | `images/03_oled_startup.jpg` | User interface / Benutzeroberfläche |
| 04 | `images/04_cad_sensor_vent.png` | Weather sensor mounting / Sensorbelüftung |
| 05 | `images/05_usb_power_measurement.jpg` | Power consumption / Energieverbrauch |
| 06 | `images/06_usb_long_run.jpg` | Continuous operation / Dauerbetrieb |
| 07 | `images/07_fusion_enclosure.png` | CAD and mechanical design / CAD und Gehäuse |
| 08 | `images/08_bambu_print_layout.png` | 3D printing / 3D-Druck |

**Editorial recommendation / Redaktionelle Empfehlung:** For a bilingual PDF, use either a two-column language layout or two mirrored language sections sharing the same numbered figures. The latter is easier to read on mobile devices and permits larger photographs. For print, export images at sufficient resolution and avoid treating CAD screenshots as manufacturing drawings. / Für ein zweisprachiges PDF empfehlen sich entweder zwei Sprachspalten oder zwei spiegelgleich aufgebaute Sprachabschnitte mit derselben Abbildungsnummerierung. Letzteres ist auf mobilen Geräten angenehmer und lässt den Fotos mehr Raum. CAD-Screenshots ersetzen keine bemaßten Fertigungszeichnungen.

## B. Proposed GitHub layout / Vorschlag für die GitHub-Struktur

```text
SailSense/
├── README.md
├── LICENSE                      # choose / Lizenz festlegen
├── requirements.txt              # to create / noch erstellen
├── config/
│   └── settings.example.yaml     # sanitised example / bereinigtes Muster
├── src/
│   └── sailsense/
├── scripts/
├── tests/                        # automated tests / automatisierte Tests
├── hardware/
│   ├── cad/
│   │   └── sailsense.f3d
│   ├── print/
│   │   └── sailsense.3mf
│   ├── wiring/                    # future schematic / Schaltplan folgt
│   └── bom/                       # future bill of materials / Stückliste folgt
├── docs/
│   ├── SailSense_Dokumentation_DE_EN.md
│   └── images/
└── .gitignore
```

The provided `.f3d` and `.3mf` are **design artefacts**; they have not been modified or verified for printability as part of this text preparation. The repository layout above is a proposal, not a claim that the listed missing files already exist. / Die vorliegenden `.f3d`- und `.3mf`-Dateien sind **Konstruktionsdateien**; sie wurden für diese Dokumentation weder verändert noch auf Druckbarkeit geprüft. Die Verzeichnisstruktur ist ein Vorschlag, keine Behauptung, dass die derzeit fehlenden Dateien schon vorhanden wären.

## C. Scope, safety and verification / Geltungsbereich, Sicherheit und Prüfung

- **Verified in the provided source / Im Quellcode nachvollzogen:** Python modules and config for GPS, BME280, track logging, GPX, OLED views, barograph, anchor watch, LED, buzzer and buttons.
- **Visible in supplied photographs / Auf Bildern erkennbar:** Breadboard prototype, connected Raspberry Pi, OLED start-up, USB power measurements and CAD enclosure designs.
- **Not independently tested here / Nicht unabhängig getestet:** Functional GPIO wiring, power-bank runtime, GPS precision, long-term service stability, anchor-alarm reliability and physical fit of the 3D-printed case.
- **Planned / Geplant:** MPU integration, web control, revised button placement, improved BME sensor mounting, comprehensive power optimisation, installation automation and robust failure recovery.
- **Safety / Sicherheit:** SailSense does not replace certified maritime navigation equipment, weather forecasting services or independent anchor-watch procedures. / SailSense ersetzt keine zugelassene nautische Ausrüstung, keine Wettervorhersage und keine unabhängige Ankerkontrolle.

*Prepared from the supplied SailSense source and design files on 1 November 2026. / Erstellt auf Grundlage der übermittelten SailSense-Quell- und Konstruktionsdateien am 1. November 2026.*
