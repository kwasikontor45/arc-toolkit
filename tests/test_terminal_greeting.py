import os,subprocess,tempfile, pathlib,unittest,re,statistics,time
SOURCE=str(pathlib.Path(__file__).resolve().parents[1] / "config" / "greeting.sh")
class GreetingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix="arc-ready-test-")
  self.root=pathlib.Path(self.tmp.name); self.bin=self.root/"bin";self.bin.mkdir()
  self.home=self.root/"home";self.home.mkdir()
  (self.home/".config/arc").mkdir(parents=True)
  (self.home/".local/share/lt").mkdir(parents=True)
  (self.home/".config/arc/motd").write_text("I–III: WWSJD · Right & tight · Swiss cheese\nKHAOS-LAB: DEV-STUDIO\nMO: ~/dev-notes/intel-ops/MO.md\n")
  (self.home/".local/share/lt/focus").write_text("a-long-process-name-"*8)
  self.log=self.root/"probes"
  bodies={
   "free": "printf '              total used free shared buff/cache available\\nMem: 7.7Gi 3.3Gi 1Gi 0B 3Gi 4.4Gi\\nSwap: 7.9Gi 0B 7.9Gi\\n'",
   "df":"printf 'df-args:%s\\n' \"$*\" >> \"$TEST_PROBE_LOG\"; printf 'Filesystem Size Used Avail Use%% Mounted\\nrootfs 122G 52G 70G 43%% /\\n'",
   "ip":"if [ \"$TEST_STATE\" = up ]; then printf 'proton0 UNKNOWN 10.2.0.2/32\\n'; fi",
   "hostname":"if [ \"$1\" = -I ]; then [ \"$TEST_STATE\" != up ] || printf '192.0.2.2\\n'; else printf '%s\\n' \"${TEST_NODE:-fixture}\"; fi",
   "id":"printf '%s\n' \"${TEST_USER:-fixture-user}\"",
   "systemctl":"if [ \"$TEST_STATE\" != up ]; then printf 'inactive\\n'; exit 3; fi; case \"$*\" in *--quiet*) ;; *) printf 'active\\n';; esac",
   "pgrep":"[ \"$TEST_STATE\" = up ]",
   "mountpoint":"[ \"$TEST_STATE\" = up ]",
   "ls":"[ \"$TEST_STATE\" = up ]",
   "arc":"[ \"$TEST_STATE\" != missing ] && printf 'austere / aw-steer · adjective · plain, restrained, and without excess\\n'",
   "protonvpn":"[ \"$TEST_STATE\" != up ] || printf 'Server: US#1\\n'",
   "nmcli":"exit 1",
   "curl":"exit 99"}
  for name,body in bodies.items():
   p=self.bin/name;p.write_text("#!/bin/sh\nprintf '%s\\n' '"+name+"' >> \"$TEST_PROBE_LOG\"\n"+("if [ \"$TEST_STATE\" = broken ]; then exit 127; fi\n" if name not in ("arc","curl") else "")+body+"\n");p.chmod(0o700)
  self.env={**os.environ,"HOME":str(self.home),"XDG_CACHE_HOME":str(self.home/".cache"),"TMPDIR":str(self.root),"PATH":str(self.bin)+":"+os.environ["PATH"],"TEST_PROBE_LOG":str(self.log),"TEST_STATE":"up","TEST_NODE":"fixture","TEST_USER":"fixture-user","HOSTNAME":"fixture","COLUMNS":"96","LC_ALL":"C.UTF-8","TERM":"xterm-256color","NO_COLOR":"1","SHELL":"/bin/bash"}
  self.code="source "+SOURCE+"; _arc_greeting_public_ipv4() { printf '198.51.100.2'; }; _arc_greeting_configured_isp_ip() { printf '192.0.2.1'; }; _arc_greeting"
 def tearDown(self):self.tmp.cleanup()
 def runGreeting(self,shell="zsh",**env):
  r=subprocess.run([shell,"-f","-c",self.code],env={**self.env,**env},capture_output=True,text=True,timeout=8)
  self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(r.stderr,"")
  return r.stdout
 def test_cache(self):
  a=self.runGreeting(); first=self.log.read_text()
  b=self.runGreeting()
  self.assertEqual(a,b);self.assertEqual([x for x in first.splitlines() if x!="id"],[x for x in self.log.read_text().splitlines() if x!="id"])
  self.assertEqual(first.splitlines().count("free"),1)
  self.assertLessEqual(first.splitlines().count("df"),3)
  self.assertIn("[ STATION_READY ]",a)
 def test_degraded(self):
  for shell in ("bash","zsh"):
   for state in ("down","broken","missing"):
    out=self.runGreeting(shell,TEST_STATE=state,ARC_GREETING_CACHE="0")
    self.assertIn("HOST",out);self.assertIn("LOCAL_RADAR",out);self.assertNotIn("\x1b",out)
    self.assertTrue("DIRECT_ROUTE" in out or "NO_CARRIER" in out or "NETWORK_UNKNOWN" in out)
    if state=="broken":
     self.assertIn("unknown",out)
     self.assertRegex(out,r"DISK\s+unavailable")
    if state=="missing":self.assertIn("unavailable",out)
 def test_modes(self):
  for shell in ("bash","zsh"):
   for width in (24,52,80,90,96,160):
    out=self.runGreeting(shell,COLUMNS=str(width),ARC_GREETING_CACHE="0")
    self.assertLessEqual(max(map(len,out.splitlines())),min(width,96))
    content=[(re.findall(r"\|([^|]*)\|",line)[0].strip() if "|" in line and re.findall(r"\|([^|]*)\|",line) else line.strip()) for line in out.splitlines()]
    self.assertIn("a-long-process-name-"*8,"".join(content))
   asciiOut=self.runGreeting(shell,LC_ALL="C",ARC_GREETING_CACHE="0")
   self.assertTrue(asciiOut.isascii());self.assertNotIn("\x1b",asciiOut)
   plain=self.runGreeting(shell,ARC_GREETING_STYLE="plain",ARC_GREETING_CACHE="0")
   self.assertNotIn("|___",plain)
 def test_invalid_cache_and_invalidation(self):
  self.runGreeting()
  cache=self.home/".cache/arc/greeting-snapshots/station"
  cache.write_text("bad\n")
  self.assertIn("HOST",self.runGreeting())
  focus=self.home/".local/share/lt/focus";focus.write_text("new-focus")
  self.assertIn("new-focus",self.runGreeting())
 def test_pipefail_errexit(self):
  for shell in ("bash","zsh"):
   self.code="set -e; set -o pipefail; "+self.code+"; printf '\\nSURVIVED\\n'"
   self.assertIn("SURVIVED",self.runGreeting(shell,TEST_STATE="broken",ARC_GREETING_CACHE="0"))

 def test_cache_expiry_permissions_and_truncation(self):
  self.runGreeting()
  cache=self.home/".cache/arc/greeting-snapshots/station"
  self.assertEqual(cache.stat().st_mode & 0o777,0o600)
  self.assertEqual(cache.parent.stat().st_mode & 0o777,0o700)
  lines=cache.read_text().splitlines()
  lines[0]="0";cache.write_text("\n".join(lines)+"\n")
  self.assertIn("HOST",self.runGreeting())
  cache.chmod(0o666)
  self.assertIn("HOST",self.runGreeting())
  self.assertEqual(cache.stat().st_mode & 0o777,0o600)
  lines=cache.read_text().splitlines()
  cache.write_text("\n".join(lines[:3])+"\n")
  self.assertIn("HOST",self.runGreeting())
 def test_portable_identity_updates_cache(self):
  first=self.runGreeting(TEST_NODE="node-a",TEST_USER="user-a",HOSTNAME="node-a")
  self.assertIn("IDENTITY   lt · node-a · arc",first)
  self.assertIn("USER       user-a",first)
  second=self.runGreeting(TEST_NODE="node-b",TEST_USER="user-b",HOSTNAME="node-b")
  self.assertIn("IDENTITY   lt · node-b · arc",second)
  self.assertIn("USER       user-b",second)

 def test_cloud_profile(self):
  out=self.runGreeting(ARC_GREETING_PROFILE="cloud")
  self.assertIn("ORIGIN",out);self.assertIn("SESSION",out)
  self.assertNotIn("EXT ",out);self.assertNotIn("WOD",out)
  self.assertIn("df-args:-h /",self.log.read_text())
  self.assertFalse((self.home/".cache/arc/greeting-snapshots/station").exists())
 def test_no_temp_storage(self):
  self.assertIn("Greeting unavailable",self.runGreeting(TMPDIR=str(self.root/"missing"),ARC_GREETING_CACHE="0"))


 def test_cockpit_panels_and_flight_deck_identity(self):
  out=self.runGreeting(COLUMNS="96",ARC_GREETING_CACHE="0")
  self.assertRegex(out,r"(?m)^\s+RIG 418 ·  b6ones6aw · ARCHITECT-OF-CHAOS$")
  self.assertRegex(out,r"\[ (?:NYX|CHOICE|DESIRE|STILL-PINE) \]")
  header=out.splitlines()[0]
  self.assertRegex(header,r"^\s+RIG 418 ·  b6ones6aw · ARCHITECT-OF-CHAOS$")
  self.assertGreater(len(header)-len(header.lstrip()),15)
  brand=next(line for line in out.splitlines() if "KHAOS-LAB" in line)
  self.assertGreater(len(brand)-len(brand.lstrip()),25)
  time_line=next(line for line in out.splitlines() if "LOCAL_TIME" in line)
  self.assertRegex(time_line,r"\[ (?:NYX|CHOICE|DESIRE|STILL-PINE) \]")
  self.assertNotRegex(time_line,r"· still-pine$")
  self.assertIn("⌜ OPERATIONS",out);self.assertIn("⌜ SYSTEMS",out)
  self.assertIn("⌜ KHAOS-LAB",out)
  self.assertIn("DEV-STUDIO",out)
  self.assertNotIn("KATALEYA",out);self.assertNotIn("COMPANION",out)
  from datetime import date
  sunTzuQuotes=("All warfare is based on deception.","Attack him where he is unprepared.","Appear weak when you are strong.")
  self.assertIn("SUN TZU",out)
  self.assertIn(sunTzuQuotes[(date.today().toordinal()-1)%len(sunTzuQuotes)],out)
  motto=next(line for line in out.splitlines() if "E Pluribus" in line)
  self.assertIn("☠️💀☠️",motto)
  import unicodedata
  motto_width=sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ("W","F") else 1 for c in motto.strip())
  self.assertEqual(len(motto)-len(motto.lstrip()),2+(92-motto_width)//2)
  self.assertNotIn("//",out)
  self.assertNotIn("||_/",out);self.assertNotIn("____/",out)
  self.assertIn("IDENTITY   lt · fixture · arc",out)
  self.assertIn("USER       fixture-user",out)
  self.assertNotIn("LOAD",out)
  self.assertRegex(out,r"HOST\s+swap 0B/7.9Gi · shell bash")
  self.assertRegex(out,r"DISK\s+122G total · 52G used · 70G free")
  self.assertIn("df-args:-h /",self.log.read_text().splitlines())
  self.assertNotIn("rootfs",out)
  self.assertNotIn("+---",out);self.assertNotIn("|___",out)
 def test_ship_rule_uses_dots_not_underscores(self):
  code="source "+SOURCE+"; _ARC_GREETING_SHIP=1; COLUMNS=52; _arc_greeting_rule"
  result=subprocess.run(["bash","-c",code],env=self.env,capture_output=True,text=True,timeout=3)
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn("................",result.stdout)
  self.assertNotIn("________",result.stdout)

 def test_plain_cockpit_markers_are_ascii_and_art_free(self):
  out=self.runGreeting(ARC_GREETING_STYLE="plain",COLUMNS="52",ARC_GREETING_CACHE="0")
  self.assertIn("> OPERATIONS",out);self.assertIn("> KHAOS-LAB - DEV-STUDIO",out)
  marker_lines=[line for line in out.splitlines() if line.strip().startswith(">")]
  self.assertTrue(marker_lines and all(line.isascii() for line in marker_lines))
  self.assertNotIn("//",out);self.assertNotIn("____/",out);self.assertNotIn("||_/",out)

 def test_circadian_phase_schedule_boundaries(self):
  code="source "+SOURCE+"; _arc_greeting_clock() { printf '%s\\n' \"$TEST_HOUR\"; }; _arc_greeting_current_phase"
  expected={"0":"nyx","5":"nyx","6":"choice","10":"choice","11":"desire","16":"desire","17":"still-pine","20":"still-pine","21":"nyx","23":"nyx"}
  for hour,phase in expected.items():
   result=subprocess.run(["bash","-c",code],env={**self.env,"TEST_HOUR":hour},capture_output=True,text=True,timeout=3)
   self.assertEqual(result.returncode,0,result.stderr)
   self.assertEqual(result.stdout.strip(),phase)

 def test_circadian_color_is_limited_to_live_phase_signals(self):
  rows=self.root/"circadian-fixture.tsv"
  fixture="WOD\tgossamer / gos-uh-mer · noun · a very light, delicate material or thread\n@SECTION\tOPERATIONS\nRAM\t3.3Gi/7.7Gi used · 4.4Gi free\t\\033[38;2;226;229;233m\n@SECTION\tSYSTEMS\nHOST\tswap 0B/7.9Gi · shell zsh 5.9/omz\t\\033[38;2;226;229;233m\n@SECTION\tRADAR & NAV\nLOCAL_TIME\tSun, 18 Oct 2026 · 05:55:45 PDT · PHASE\t\\033[38;2;226;229;233m\n@MOTTO\tE Pluribus Unum · ☠️💀☠️ · In God We Trust ✧ ✧\n"
  palette={"nyx":"234;154;151","choice":"94;200;237","desire":"246;193;119","still-pine":"196;167;231"}
  for phase,rgb in palette.items():
   rows.write_text(fixture.replace("PHASE",phase))
   code="source "+SOURCE+"; _arc_greeting_cockpit_render \""+str(rows)+"\" 96 "+phase+" 1 cockpit"
   result=subprocess.run(["bash","-c",code],env={**self.env,"NO_COLOR":"","_ARC_GREETING_COLOR":"1"},capture_output=True,text=True,timeout=5)
   self.assertEqual(result.returncode,0,result.stderr)
   plain_output=re.sub(r"\x1b\[[0-9;]*m","",result.stdout)
   time_line=next(line for line in plain_output.splitlines() if "LOCAL_TIME" in line)
   self.assertIn("[ "+phase.upper()+" ]",time_line)
   self.assertIn("\x1b[38;2;164;194;139mRIG ",result.stdout)
   self.assertIn("\x1b[1;38;2;255;68;92m418\x1b[0m",result.stdout)
   self.assertIn("\x1b[1;38;2;"+rgb+"m[ "+phase.upper()+" ]",result.stdout)
   self.assertIn("\x1b[38;2;234;154;151mgossamer",result.stdout)
   self.assertIn("\x1b[38;2;245;198;215mE Pluribus",result.stdout)
   self.assertNotIn("LOAD",result.stdout)
   self.assertIn("⌜ WOD · INTERCEPT",plain_output)
   self.assertNotIn("//",plain_output)
   plain=re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]","",result.stdout)
   lines=plain.splitlines(); motto=next(i for i,line in enumerate(lines) if "E Pluribus" in line)
   self.assertTrue(lines[motto-1].strip().startswith("LOCAL_TIME"))

 def test_unicode_focus_cells(self):
  import unicodedata
  (self.home/".local/share/lt/focus").write_text("界"*30+" e\u0301"*8)
  out=self.runGreeting(COLUMNS="96",ARC_GREETING_CACHE="0")
  for line in out.splitlines():
   width=sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in ("W","F") else 1 for c in line)
   self.assertLessEqual(width,96)

if __name__=="__main__":unittest.main()
