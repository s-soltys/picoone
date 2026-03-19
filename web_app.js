(function () {
  if (!window.preact || !window.preactHooks || !window.htm) {
    return;
  }

  var h = preact.h;
  var render = preact.render;
  var html = htm.bind(h);
  var useEffect = preactHooks.useEffect;
  var useState = preactHooks.useState;

  var ROUTE_TITLES = {
    "/": "PicoOne",
    "/led": "LED Control",
    "/notes": "Notes",
    "/sysinfo": "System Info",
    "/morse": "Morse Code",
    "/wifi": "WiFi Manager",
    "/wifi/scan": "WiFi Scan",
  };

  var ROUTE_SUBTITLES = {
    "/": "pico.local",
    "/led": "Switch the onboard LED pattern running on the Pico.",
    "/notes": "Keep quick notes on the device.",
    "/sysinfo": "Live hardware and Wi-Fi telemetry.",
    "/morse": "Blink text back out over the LED.",
    "/wifi": "Manage saved networks and trigger joins.",
    "/wifi/scan": "Scan nearby 2.4 GHz networks and join them.",
  };

  function normalizeRoute(route) {
    var next = route || "/";
    if (next.charAt(0) !== "/") {
      next = "/" + next;
    }
    if (!ROUTE_TITLES[next]) {
      next = "/";
    }
    return next;
  }

  function currentRoute() {
    var hash = window.location.hash || "#/";
    if (hash.charAt(0) === "#") {
      hash = hash.slice(1);
    }
    return normalizeRoute(hash || "/");
  }

  function routeHref(route) {
    return "#" + normalizeRoute(route);
  }

  function emptyWifiCurrent() {
    return { connected: false, ssid: "", ip: "", rssi: 0 };
  }

  function normalizeBootstrap(data) {
    var src = data || {};
    return {
      ready: !!data,
      patternNames: src.pattern_names || [],
      ledMode: typeof src.led_mode === "number" ? src.led_mode : 0,
      notes: src.notes || [],
      sysinfo: src.sysinfo || null,
      wifiCurrent: src.wifi_current || emptyWifiCurrent(),
      wifiProfiles: src.wifi_profiles || [],
    };
  }

  function cloneObject(source) {
    var out = {};
    var key;
    for (key in source) {
      out[key] = source[key];
    }
    return out;
  }

  function apiJSON(path, options) {
    return fetch(path, options).then(function (response) {
      return response.json();
    });
  }

  function postPlain(path, body) {
    return apiJSON(path, { method: "POST", body: body });
  }

  function connectMessage(ssid, data) {
    if (data && data.ok && data.pending) {
      return (
        "Trying to join " +
        ssid +
        ". This page may stop updating while PicoOne switches networks. Reopen http://pico.local/ after it reconnects."
      );
    }
    if (data && data.busy) {
      return "Another Wi-Fi connection attempt is already in progress.";
    }
    return "Failed to start connection to " + ssid + ".";
  }

  function Header(props) {
    if (props.route === "/") {
      return html`
        <div class="panel">
          <h1 class="title">PicoOne</h1>
          <p class="sub">pico.local</p>
          <p class="sub">Served by the Pico, routed as a single-page app, rendered with CDN-hosted Preact.</p>
        </div>
      `;
    }
    return html`
      <div class="toolbar">
        <button onClick=${props.onHome}>Home</button>
        <span class="pill">pico.local</span>
      </div>
      <div class="panel">
        <h1 class="title">${ROUTE_TITLES[props.route]}</h1>
        <p class="sub">${ROUTE_SUBTITLES[props.route]}</p>
      </div>
    `;
  }

  function HomeView(props) {
    var cards = [
      { route: "/led", title: "LED Control", desc: props.patternNames.length + " patterns" },
      { route: "/notes", title: "Notes", desc: "Quick notes" },
      { route: "/sysinfo", title: "System Info", desc: "Live stats" },
      { route: "/morse", title: "Morse Code", desc: "Blink text" },
      { route: "/wifi", title: "WiFi", desc: "Manage networks" },
    ];
    return html`
      <div class="home-grid">
        ${cards.map(function (card) {
          return html`
            <a key=${card.route} class="card" href=${routeHref(card.route)}>
              <h2>${card.title}</h2>
              <p>${card.desc}</p>
            </a>
          `;
        })}
      </div>
    `;
  }

  function InfoRows(props) {
    if (!props.rows || !props.rows.length) {
      return html`<div class="panel"><div class="empty">Nothing to show.</div></div>`;
    }
    return html`
      <div class="panel">
        ${props.rows.map(function (row, index) {
          return html`
            <div key=${index} class="row">
              <span class="k">${row[0]}</span>
              <span class="v">${row[1]}</span>
            </div>
          `;
        })}
      </div>
    `;
  }

  function LedView(props) {
    return html`
      <div class="grid">
        ${props.patternNames.map(function (name, index) {
          return html`
            <button
              key=${name}
              class=${index === props.ledMode ? "active" : ""}
              onClick=${function () {
                props.onPick(index);
              }}
            >
              ${name}
            </button>
          `;
        })}
      </div>
    `;
  }

  function NotesView(props) {
    return html`
      <div class="panel">
        <div class="note-form">
          <textarea
            class="field"
            placeholder="Write a note..."
            value=${props.noteDraft}
            onInput=${function (event) {
              props.onDraft(event.currentTarget.value);
            }}
          ></textarea>
          <button class="primary" disabled=${props.busy} onClick=${props.onAdd}>Add Note</button>
        </div>
        ${props.notes.length
          ? html`
              <div class="stack">
                ${props.notes.map(function (note, index) {
                  return html`
                    <div key=${index} class="note">
                      <div>${note}</div>
                      <div class="spacer"></div>
                      <div class="acts">
                        <span
                          onClick=${function () {
                            props.onEdit(index);
                          }}
                        >
                          edit
                        </span>
                        <span
                          onClick=${function () {
                            props.onDelete(index);
                          }}
                        >
                          del
                        </span>
                      </div>
                    </div>
                  `;
                })}
              </div>
            `
          : html`<div class="empty">No notes yet.</div>`}
      </div>
    `;
  }

  function SysinfoView(props) {
    if (props.error) {
      return html`<div class="status bad">${props.error}</div>`;
    }
    if (!props.info) {
      return html`<div class="panel"><div class="empty">Loading system info...</div></div>`;
    }
    var rows = [
      ["Temperature", props.info.temp_c + " C"],
      ["CPU", props.info.cpu_mhz + " MHz"],
      ["RAM", props.info.ram_free_kb + " / " + props.info.ram_total_kb + " KB (" + props.info.ram_pct + "% used)"],
      ["Uptime", props.info.uptime],
      ["WiFi Network", props.info.ssid],
      ["WiFi RSSI", props.info.rssi + " dBm"],
      ["IP", props.info.ip],
    ];
    return html`<${InfoRows} rows=${rows} />`;
  }

  function MorseView(props) {
    return html`
      <div class="panel">
        <div class="stack">
          <input
            class="field"
            type="text"
            placeholder="Type your message..."
            value=${props.text}
            onInput=${function (event) {
              props.onText(event.currentTarget.value);
            }}
          />
          <label class="sub">
            Speed: <strong>${props.wpm}</strong> WPM
          </label>
          <input
            type="range"
            min="5"
            max="25"
            value=${props.wpm}
            onInput=${function (event) {
              props.onWpm(parseInt(event.currentTarget.value, 10) || 12);
            }}
          />
          <div class="ctr">
            <button class="primary" disabled=${props.busy} onClick=${props.onSend}>Send via LED</button>
          </div>
          ${props.status ? html`<div class="status neutral">${props.status}</div>` : null}
        </div>
      </div>
    `;
  }

  function WifiCurrentCard(props) {
    if (!props.current.connected) {
      return html`<div class="status bad">Not connected</div>`;
    }
    return html`
      <div class="status good">
        Connected to <strong>${props.current.ssid}</strong><br />
        ${props.current.ip} (${props.current.rssi} dBm)
      </div>
    `;
  }

  function WifiView(props) {
    return html`
      <div class="stack">
        <div class="panel">
          <h2>Current Connection</h2>
          <div class="spacer"></div>
          <${WifiCurrentCard} current=${props.current} />
        </div>
        ${props.message ? html`<div class="status neutral">${props.message}</div>` : null}
        <div class="nav">
          <a class="btn" href=${routeHref("/wifi/scan")}>Scan Networks</a>
        </div>
        <div class="panel">
          <h2>Saved Networks</h2>
          <p class="sub">Priority order decides what the Pico tries first on boot.</p>
          <div class="spacer"></div>
          ${props.profiles.length
            ? html`
                <div class="stack">
                  ${props.profiles.map(function (profile, index) {
                    return html`
                      <div key=${profile.ssid + ":" + index} class="prof">
                        <div class="split">
                          <div>
                            <strong>${profile.ssid}</strong>
                            <div class="meta">${profile.password ? "Password saved" : "Open network"}</div>
                          </div>
                          <div class="acts">
                            <span
                              onClick=${function () {
                                props.onConnect(profile.ssid, profile.password || "");
                              }}
                            >
                              join
                            </span>
                            <span
                              onClick=${function () {
                                props.onEdit(index);
                              }}
                            >
                              edit
                            </span>
                            ${index > 0
                              ? html`
                                  <span
                                    onClick=${function () {
                                      props.onMove(index, -1);
                                    }}
                                  >
                                    up
                                  </span>
                                `
                              : null}
                            ${index < props.profiles.length - 1
                              ? html`
                                  <span
                                    onClick=${function () {
                                      props.onMove(index, 1);
                                    }}
                                  >
                                    down
                                  </span>
                                `
                              : null}
                            <span
                              onClick=${function () {
                                props.onDelete(index);
                              }}
                            >
                              del
                            </span>
                          </div>
                        </div>
                      </div>
                    `;
                  })}
                </div>
              `
            : html`<div class="empty">No saved networks.</div>`}
        </div>
        <div class="panel">
          <h2>${props.editIndex >= 0 ? "Edit Network" : "Add Network"}</h2>
          <div class="spacer"></div>
          <div class="stack">
            <input
              class="field"
              type="text"
              placeholder="SSID"
              value=${props.ssid}
              onInput=${function (event) {
                props.onSsid(event.currentTarget.value);
              }}
            />
            <input
              class="field"
              type="password"
              placeholder="Password (leave blank for open network)"
              value=${props.password}
              onInput=${function (event) {
                props.onPassword(event.currentTarget.value);
              }}
            />
            <div class="ctr">
              <button class="primary" disabled=${props.busy} onClick=${props.onSave}>
                ${props.editIndex >= 0 ? "Update Network" : "Save Network"}
              </button>
              ${props.editIndex >= 0
                ? html`<button disabled=${props.busy} onClick=${props.onCancel}>Cancel</button>`
                : null}
            </div>
            <div class="footer-note">Save networks here, then use Join from the saved list when needed.</div>
          </div>
        </div>
      </div>
    `;
  }

  function WifiScanView(props) {
    return html`
      <div class="stack">
        <div class="panel">
          <h2>Current Connection</h2>
          <div class="spacer"></div>
          <${WifiCurrentCard} current=${props.current} />
        </div>
        ${props.message ? html`<div class="status neutral">${props.message}</div>` : null}
        <div class="nav">
          <a class="btn" href=${routeHref("/wifi")}>Saved Networks</a>
          <button onClick=${props.onScan} disabled=${props.busy}>${props.busy ? "Scanning..." : "Rescan"}</button>
        </div>
        ${props.error ? html`<div class="status bad">${props.error}</div>` : null}
        <div class="panel">
          <h2>Available Networks</h2>
          <div class="spacer"></div>
          ${props.networks.length
            ? html`
                <div class="stack">
                  ${props.networks.map(function (network, index) {
                    var showForm = !!props.open[index];
                    return html`
                      <div key=${network.ssid + ":" + index} class="net">
                        <div class="split">
                          <div>
                            <strong>${network.ssid}</strong>
                            <div class="meta">
                              ${network.rssi} dBm
                              ${network.saved ? html`<span class="pill">saved</span>` : null}
                              <span class="pill">${network.secure ? "secured" : "open"}</span>
                            </div>
                          </div>
                          <button
                            onClick=${function () {
                              props.onToggle(index);
                            }}
                          >
                            ${network.secure ? "Join" : "Join Open"}
                          </button>
                        </div>
                        ${network.secure && showForm
                          ? html`
                              <div class="conn-form">
                                <input
                                  class="field"
                                  type="password"
                                  placeholder="Password"
                                  value=${props.passwords[index] || ""}
                                  onInput=${function (event) {
                                    props.onPassword(index, event.currentTarget.value);
                                  }}
                                />
                                <button
                                  class="primary"
                                  onClick=${function () {
                                    props.onConnect(index);
                                  }}
                                >
                                  Connect
                                </button>
                              </div>
                            `
                          : null}
                      </div>
                    `;
                  })}
                </div>
              `
            : html`<div class="empty">${props.busy ? "Scanning..." : "No networks found."}</div>`}
        </div>
      </div>
    `;
  }

  function App() {
    var initial = normalizeBootstrap(window.__PICO_BOOTSTRAP__);
    var [route, setRoute] = useState(currentRoute());
    var [ready, setReady] = useState(initial.ready);
    var [bootError, setBootError] = useState("");
    var [patternNames, setPatternNames] = useState(initial.patternNames);
    var [ledMode, setLedMode] = useState(initial.ledMode);
    var [notes, setNotes] = useState(initial.notes);
    var [sysinfo, setSysinfo] = useState(initial.sysinfo);
    var [sysinfoError, setSysinfoError] = useState("");
    var [noteDraft, setNoteDraft] = useState("");
    var [noteBusy, setNoteBusy] = useState(false);
    var [morseText, setMorseText] = useState("");
    var [morseWpm, setMorseWpm] = useState(12);
    var [morseStatus, setMorseStatus] = useState("");
    var [morseBusy, setMorseBusy] = useState(false);
    var [wifiCurrent, setWifiCurrent] = useState(initial.wifiCurrent);
    var [wifiProfiles, setWifiProfiles] = useState(initial.wifiProfiles);
    var [wifiMessage, setWifiMessage] = useState("");
    var [wifiBusy, setWifiBusy] = useState(false);
    var [wifiEditIndex, setWifiEditIndex] = useState(-1);
    var [wifiSsid, setWifiSsid] = useState("");
    var [wifiPassword, setWifiPassword] = useState("");
    var [scanBusy, setScanBusy] = useState(false);
    var [scanError, setScanError] = useState("");
    var [scanNetworks, setScanNetworks] = useState([]);
    var [scanOpen, setScanOpen] = useState({});
    var [scanPasswords, setScanPasswords] = useState({});

    function applyBootstrap(data) {
      var next = normalizeBootstrap(data);
      setPatternNames(next.patternNames);
      setLedMode(next.ledMode);
      setNotes(next.notes);
      setSysinfo(next.sysinfo);
      setWifiCurrent(next.wifiCurrent);
      setWifiProfiles(next.wifiProfiles);
      setReady(true);
      setBootError("");
    }

    function refreshBootstrap() {
      return apiJSON("/api/bootstrap")
        .then(function (data) {
          applyBootstrap(data);
        })
        .catch(function () {
          setBootError("Unable to load PicoOne state from the device.");
        });
    }

    function refreshWifiCurrent() {
      return apiJSON("/api/wifi/status").then(function (data) {
        setWifiCurrent(data);
        return data;
      });
    }

    function refreshProfiles() {
      return apiJSON("/api/wifi/profiles").then(function (data) {
        setWifiProfiles(data);
        return data;
      });
    }

    function refreshSysinfo() {
      return apiJSON("/api/sysinfo")
        .then(function (data) {
          setSysinfo(data);
          setSysinfoError("");
          return data;
        })
        .catch(function () {
          setSysinfoError("Unable to read system info right now.");
        });
    }

    function scanWifi() {
      setScanBusy(true);
      setScanError("");
      return apiJSON("/api/wifi/scan")
        .then(function (data) {
          setScanNetworks(data);
          return data;
        })
        .catch(function () {
          setScanError("Scanning failed. Try again in a moment.");
          setScanNetworks([]);
        })
        .then(function (data) {
          setScanBusy(false);
          return data;
        });
    }

    function goHome() {
      window.location.hash = "#/";
    }

    useEffect(function () {
      function onHashChange() {
        setRoute(currentRoute());
      }
      window.addEventListener("hashchange", onHashChange);
      return function () {
        window.removeEventListener("hashchange", onHashChange);
      };
    }, []);

    useEffect(function () {
      if (!ready) {
        refreshBootstrap();
      }
    }, [ready]);

    useEffect(function () {
      if (route !== "/sysinfo") {
        return;
      }
      refreshSysinfo();
      var timer = setInterval(refreshSysinfo, 2000);
      return function () {
        clearInterval(timer);
      };
    }, [route]);

    useEffect(function () {
      if (route !== "/wifi") {
        return;
      }
      refreshWifiCurrent();
      refreshProfiles();
    }, [route]);

    useEffect(function () {
      if (route !== "/wifi/scan") {
        return;
      }
      refreshWifiCurrent();
      scanWifi();
    }, [route]);

    function selectLed(mode) {
      apiJSON("/set?mode=" + mode)
        .then(function (data) {
          setLedMode(data.mode);
        })
        .catch(function () {
          setBootError("LED mode update failed.");
        });
    }

    function addNote() {
      if (!noteDraft.trim() || noteBusy) {
        return;
      }
      setNoteBusy(true);
      postPlain("/notes/add", noteDraft)
        .then(function (data) {
          setNotes(data.notes || []);
          setNoteDraft("");
        })
        .catch(function () {
          setBootError("Adding the note failed.");
        })
        .then(function () {
          setNoteBusy(false);
        });
    }

    function deleteNoteAt(index) {
      postPlain("/notes/del?i=" + index, "")
        .then(function (data) {
          setNotes(data.notes || []);
        })
        .catch(function () {
          setBootError("Deleting the note failed.");
        });
    }

    function editNoteAt(index) {
      var current = notes[index] || "";
      var next = window.prompt("Edit note:", current);
      if (next === null || !next.trim()) {
        return;
      }
      postPlain("/notes/edit", String(index) + "\n" + next)
        .then(function (data) {
          setNotes(data.notes || []);
        })
        .catch(function () {
          setBootError("Editing the note failed.");
        });
    }

    function sendMorse() {
      if (!morseText.trim() || morseBusy) {
        return;
      }
      setMorseBusy(true);
      setMorseStatus("Sending...");
      postPlain("/api/morse?wpm=" + morseWpm, morseText)
        .then(function (data) {
          setMorseStatus(data.ok ? "Blinking now!" : "Busy");
        })
        .catch(function () {
          setMorseStatus("Sending failed.");
        })
        .then(function () {
          setMorseBusy(false);
        });
    }

    function resetWifiForm() {
      setWifiEditIndex(-1);
      setWifiSsid("");
      setWifiPassword("");
    }

    function connectWifi(ssid, password) {
      setWifiMessage("Starting connection to " + ssid + "...");
      setWifiBusy(true);
      postPlain("/api/wifi/connect", ssid + "\n" + (password || ""))
        .then(function (data) {
          setWifiMessage(connectMessage(ssid, data));
          return refreshWifiCurrent().catch(function () {});
        })
        .catch(function () {
          setWifiMessage("Connection request did not complete. Refresh and try again.");
        })
        .then(function () {
          setWifiBusy(false);
        });
    }

    function saveWifiProfile() {
      var ssid = wifiSsid.trim();
      if (!ssid || wifiBusy) {
        if (!ssid) {
          setWifiMessage("SSID is required.");
        }
        return;
      }
      setWifiBusy(true);
      postPlain("/api/wifi/profile", String(wifiEditIndex) + "\n" + ssid + "\n" + wifiPassword)
        .then(function (data) {
          setWifiProfiles(data || []);
          setWifiMessage("Saved " + ssid + ".");
          resetWifiForm();
        })
        .catch(function () {
          setWifiMessage("Saving the network failed.");
        })
        .then(function () {
          setWifiBusy(false);
        });
    }

    function moveWifiProfile(index, direction) {
      postPlain("/api/wifi/move?i=" + index + "&d=" + direction, "")
        .then(function (data) {
          setWifiProfiles(data || []);
          resetWifiForm();
        })
        .catch(function () {
          setWifiMessage("Reordering the network failed.");
        });
    }

    function deleteWifiProfile(index) {
      postPlain("/api/wifi/del?i=" + index, "")
        .then(function (data) {
          setWifiProfiles(data || []);
          resetWifiForm();
        })
        .catch(function () {
          setWifiMessage("Deleting the network failed.");
        });
    }

    function editWifiProfile(index) {
      var profile = wifiProfiles[index];
      if (!profile) {
        return;
      }
      setWifiEditIndex(index);
      setWifiSsid(profile.ssid);
      setWifiPassword(profile.password || "");
    }

    function toggleScan(index) {
      var network = scanNetworks[index];
      if (!network) {
        return;
      }
      if (!network.secure) {
        connectWifi(network.ssid, "");
        return;
      }
      setScanOpen(function (current) {
        var next = cloneObject(current);
        next[index] = !next[index];
        return next;
      });
    }

    function setScanPassword(index, value) {
      setScanPasswords(function (current) {
        var next = cloneObject(current);
        next[index] = value;
        return next;
      });
    }

    function connectScan(index) {
      var network = scanNetworks[index];
      if (!network) {
        return;
      }
      connectWifi(network.ssid, scanPasswords[index] || "");
    }

    var content = null;

    if (!ready) {
      content = html`<div class="panel"><div class="empty">Loading device state...</div></div>`;
    } else if (route === "/") {
      content = html`<${HomeView} patternNames=${patternNames} />`;
    } else if (route === "/led") {
      content = html`<${LedView} patternNames=${patternNames} ledMode=${ledMode} onPick=${selectLed} />`;
    } else if (route === "/notes") {
      content = html`
        <${NotesView}
          noteDraft=${noteDraft}
          notes=${notes}
          busy=${noteBusy}
          onDraft=${setNoteDraft}
          onAdd=${addNote}
          onDelete=${deleteNoteAt}
          onEdit=${editNoteAt}
        />
      `;
    } else if (route === "/sysinfo") {
      content = html`<${SysinfoView} info=${sysinfo} error=${sysinfoError} />`;
    } else if (route === "/morse") {
      content = html`
        <${MorseView}
          text=${morseText}
          wpm=${morseWpm}
          status=${morseStatus}
          busy=${morseBusy}
          onText=${setMorseText}
          onWpm=${setMorseWpm}
          onSend=${sendMorse}
        />
      `;
    } else if (route === "/wifi") {
      content = html`
        <${WifiView}
          current=${wifiCurrent}
          message=${wifiMessage}
          profiles=${wifiProfiles}
          busy=${wifiBusy}
          editIndex=${wifiEditIndex}
          ssid=${wifiSsid}
          password=${wifiPassword}
          onConnect=${connectWifi}
          onEdit=${editWifiProfile}
          onMove=${moveWifiProfile}
          onDelete=${deleteWifiProfile}
          onSsid=${setWifiSsid}
          onPassword=${setWifiPassword}
          onSave=${saveWifiProfile}
          onCancel=${resetWifiForm}
        />
      `;
    } else if (route === "/wifi/scan") {
      content = html`
        <${WifiScanView}
          current=${wifiCurrent}
          message=${wifiMessage}
          networks=${scanNetworks}
          open=${scanOpen}
          passwords=${scanPasswords}
          busy=${scanBusy}
          error=${scanError}
          onScan=${scanWifi}
          onToggle=${toggleScan}
          onPassword=${setScanPassword}
          onConnect=${connectScan}
        />
      `;
    }

    return html`
      <div class="app-shell">
        <${Header} route=${route} onHome=${goHome} />
        ${bootError ? html`<div class="status bad">${bootError}</div>` : null}
        ${content}
      </div>
    `;
  }

  render(html`<${App} />`, document.getElementById("app"));
  window.__pico_app_started = true;
})();
