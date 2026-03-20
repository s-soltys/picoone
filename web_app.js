(function () {
  if (!window.preact || !window.preactHooks || !window.htm) {
    return;
  }

  var h = preact.h;
  var render = preact.render;
  var html = htm.bind(h);
  var useEffect = preactHooks.useEffect;
  var useRef = preactHooks.useRef;
  var useState = preactHooks.useState;

  var ROUTE_TITLES = {
    "/": "PicoOne",
    "/led": "LED Control",
    "/touch": "Touch Pad",
    "/notes": "Notes",
    "/sysinfo": "System Info",
    "/morse": "Morse Code",
    "/wifi": "WiFi Manager",
    "/wifi/scan": "WiFi Scan",
  };

  var ROUTE_SUBTITLES = {
    "/": "pico.local",
    "/led": "Switch the onboard LED pattern running on the Pico.",
    "/touch": "Press and hold the pad to light the onboard LED.",
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
        <div class="card shadow-sm border-0">
          <div class="card-body p-4">
            <div class="d-flex flex-wrap justify-content-between align-items-start gap-3">
              <div>
                <h1 class="h2 mb-1">PicoOne</h1>
                <p class="text-body-secondary mb-0">pico.local</p>
              </div>
              <span class="badge rounded-pill text-bg-secondary align-self-start">CDN UI</span>
            </div>
            <p class="text-body-secondary mt-3 mb-0">
              Served by the Pico, routed as a single-page app, rendered with CDN-hosted Preact and Bootstrap.
            </p>
          </div>
        </div>
      `;
    }
    return html`
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
        <button class="btn btn-outline-secondary" onClick=${props.onHome}>Home</button>
        <span class="badge rounded-pill text-bg-secondary">pico.local</span>
      </div>
      <div class="card shadow-sm border-0">
        <div class="card-body p-4">
          <h1 class="h2 mb-2">${ROUTE_TITLES[props.route]}</h1>
          <p class="text-body-secondary mb-0">${ROUTE_SUBTITLES[props.route]}</p>
        </div>
      </div>
    `;
  }

  function HomeView(props) {
    var cards = [
      { route: "/led", title: "LED Control", desc: props.patternNames.length + " patterns" },
      { route: "/touch", title: "Touch Pad", desc: "Hold to light" },
      { route: "/notes", title: "Notes", desc: "Quick notes" },
      { route: "/sysinfo", title: "System Info", desc: "Live stats" },
      { route: "/morse", title: "Morse Code", desc: "Blink text" },
      { route: "/wifi", title: "WiFi", desc: "Manage networks" },
    ];
    return html`
      <div class="row row-cols-1 row-cols-sm-2 g-3">
        ${cards.map(function (card) {
          return html`
            <div key=${card.route} class="col">
              <a class="card h-100 shadow-sm border-0 text-decoration-none text-reset" href=${routeHref(card.route)}>
                <div class="card-body p-4">
                  <h2 class="h5 mb-2">${card.title}</h2>
                  <p class="text-body-secondary mb-0">${card.desc}</p>
                </div>
              </a>
            </div>
          `;
        })}
      </div>
    `;
  }

  function InfoRows(props) {
    if (!props.rows || !props.rows.length) {
      return html`
        <div class="card shadow-sm border-0">
          <div class="card-body p-4 text-body-secondary fst-italic text-center">Nothing to show.</div>
        </div>
      `;
    }
    return html`
      <div class="card shadow-sm border-0">
        <div class="list-group list-group-flush">
          ${props.rows.map(function (row, index) {
            return html`
              <div key=${index} class="list-group-item bg-transparent px-4 py-3">
                <div class="d-flex justify-content-between align-items-start gap-3">
                  <span class="text-body-secondary small">${row[0]}</span>
                  <span class="text-end">${row[1]}</span>
                </div>
              </div>
            `;
          })}
        </div>
      </div>
    `;
  }

  function LedView(props) {
    return html`
      <div class="card shadow-sm border-0">
        <div class="card-body p-3">
          <div class="row row-cols-1 row-cols-sm-2 g-2">
            ${props.patternNames.map(function (name, index) {
              return html`
                <div key=${name} class="col">
                  <button
                    class=${"btn w-100 py-3 " + (index === props.ledMode ? "btn-success" : "btn-outline-secondary")}
                    onClick=${function () {
                      props.onPick(index);
                    }}
                  >
                    ${name}
                  </button>
                </div>
              `;
            })}
          </div>
        </div>
      </div>
    `;
  }

  function drawTouchCanvas(canvas, active) {
    if (!canvas || !canvas.getContext) {
      return;
    }
    var ctx = canvas.getContext("2d");
    var width = canvas.width;
    var height = canvas.height;
    var centerX = width / 2;
    var centerY = height / 2 - 12;
    var outerRadius = 78;
    var innerRadius = active ? 56 : 42;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = active ? "#132218" : "#121212";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = active ? "#8dffac" : "#4a4a4a";
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.arc(centerX, centerY, outerRadius, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = active ? "#8dffac" : "#d5d5d5";
    ctx.beginPath();
    ctx.arc(centerX, centerY, innerRadius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = active ? "#061109" : "#111111";
    ctx.font = "700 24px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(active ? "ON" : "PRESS", centerX, centerY);

    ctx.fillStyle = active ? "#a6dbb4" : "#8a8a8a";
    ctx.font = "15px system-ui, sans-serif";
    ctx.fillText(active ? "Release to switch the LED off" : "Hold anywhere on the pad", centerX, height - 38);
  }

  function TouchPadView(props) {
    var canvasRef = useRef(null);

    useEffect(function () {
      props.onMode(true);
      return function () {
        props.onMode(false);
      };
    }, []);

    useEffect(function () {
      drawTouchCanvas(canvasRef.current, props.active);
    }, [props.active]);

    useEffect(function () {
      if (!props.active) {
        return;
      }
      function release() {
        props.onPress(false);
      }
      function onVisibilityChange() {
        if (document.hidden) {
          release();
        }
      }
      window.addEventListener("pointerup", release);
      window.addEventListener("pointercancel", release);
      window.addEventListener("blur", release);
      document.addEventListener("visibilitychange", onVisibilityChange);
      return function () {
        window.removeEventListener("pointerup", release);
        window.removeEventListener("pointercancel", release);
        window.removeEventListener("blur", release);
        document.removeEventListener("visibilitychange", onVisibilityChange);
      };
    }, [props.active]);

    function pressStart(event) {
      event.preventDefault();
      if (event.currentTarget && event.currentTarget.setPointerCapture && typeof event.pointerId === "number") {
        try {
          event.currentTarget.setPointerCapture(event.pointerId);
        } catch (error) {}
      }
      props.onPress(true);
    }

    function pressEnd(event) {
      if (event) {
        event.preventDefault();
      }
      props.onPress(false);
    }

    function keyDown(event) {
      if ((event.key === " " || event.key === "Enter") && !props.active) {
        event.preventDefault();
        props.onPress(true);
      }
    }

    function keyUp(event) {
      if (event.key === " " || event.key === "Enter") {
        event.preventDefault();
        props.onPress(false);
      }
    }

    return html`
      <div class="card shadow-sm border-0">
        <div class="card-body p-3 p-sm-4">
          <div class="d-flex flex-column gap-3">
            <canvas
              ref=${canvasRef}
              class=${"w-100 d-block rounded-4 border border-2 bg-body-tertiary " + (props.active ? "border-success" : "border-secondary")}
              width=${320}
              height=${280}
              tabIndex="0"
              style=${{ touchAction: "none", userSelect: "none", WebkitUserSelect: "none" }}
              onPointerDown=${pressStart}
              onPointerUp=${pressEnd}
              onPointerCancel=${pressEnd}
              onLostPointerCapture=${pressEnd}
              onContextMenu=${function (event) {
                event.preventDefault();
              }}
              onKeyDown=${keyDown}
              onKeyUp=${keyUp}
            ></canvas>
            <div class="text-center">
              <div class=${"fw-semibold " + (props.active ? "text-success" : "text-body")}>
                ${props.active ? "LED on" : "LED off"}
              </div>
              <div class="text-body-secondary small mt-1">
                Press and hold the pad. Release to turn the LED back off.
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function NotesView(props) {
    return html`
      <div class="card shadow-sm border-0">
        <div class="card-body p-4">
          <div class="d-grid gap-3">
            <textarea
              class="form-control"
              rows="4"
              placeholder="Write a note..."
              value=${props.noteDraft}
              onInput=${function (event) {
                props.onDraft(event.currentTarget.value);
              }}
            ></textarea>
            <div class="d-grid d-sm-flex justify-content-sm-start">
              <button class="btn btn-primary" type="button" disabled=${props.busy} onClick=${props.onAdd}>Add Note</button>
            </div>
            ${props.notes.length
              ? html`
                  <div class="d-grid gap-3">
                    ${props.notes.map(function (note, index) {
                      return html`
                        <div key=${index} class="card bg-body-tertiary border-secondary-subtle">
                          <div class="card-body">
                            <div style=${{ whiteSpace: "pre-wrap", wordWrap: "break-word" }}>${note}</div>
                            <div class="d-flex flex-wrap gap-2 mt-3">
                              <button
                                type="button"
                                class="btn btn-sm btn-outline-secondary"
                                onClick=${function () {
                                  props.onEdit(index);
                                }}
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                class="btn btn-sm btn-outline-danger"
                                onClick=${function () {
                                  props.onDelete(index);
                                }}
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        </div>
                      `;
                    })}
                  </div>
                `
              : html`<div class="text-body-secondary fst-italic">No notes yet.</div>`}
          </div>
        </div>
      </div>
    `;
  }

  function SysinfoView(props) {
    if (props.error) {
      return html`<div class="alert alert-danger mb-0">${props.error}</div>`;
    }
    if (!props.info) {
      return html`
        <div class="card shadow-sm border-0">
          <div class="card-body p-4 text-body-secondary fst-italic text-center">Loading system info...</div>
        </div>
      `;
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
      <div class="card shadow-sm border-0">
        <div class="card-body p-4">
          <div class="d-grid gap-3">
            <input
              class="form-control"
              type="text"
              placeholder="Type your message..."
              value=${props.text}
              onInput=${function (event) {
                props.onText(event.currentTarget.value);
              }}
            />
            <label class="form-label mb-0">
              Speed: <strong>${props.wpm}</strong> WPM
            </label>
            <input
              class="form-range"
              type="range"
              min="5"
              max="25"
              value=${props.wpm}
              onInput=${function (event) {
                props.onWpm(parseInt(event.currentTarget.value, 10) || 12);
              }}
            />
            <div class="d-grid d-sm-flex justify-content-sm-center">
              <button class="btn btn-primary" type="button" disabled=${props.busy} onClick=${props.onSend}>
                Send via LED
              </button>
            </div>
            ${props.status ? html`<div class="alert alert-secondary mb-0">${props.status}</div>` : null}
          </div>
        </div>
      </div>
    `;
  }

  function WifiCurrentCard(props) {
    if (!props.current.connected) {
      return html`<div class="alert alert-warning mb-0">Not connected</div>`;
    }
    return html`
      <div class="alert alert-success mb-0">
        Connected to <strong>${props.current.ssid}</strong>
        <div class="small mt-1">${props.current.ip} (${props.current.rssi} dBm)</div>
      </div>
    `;
  }

  function WifiView(props) {
    return html`
      <div class="d-grid gap-3">
        <div class="card shadow-sm border-0">
          <div class="card-body p-4">
            <h2 class="h5 mb-3">Current Connection</h2>
            <${WifiCurrentCard} current=${props.current} />
          </div>
        </div>
        ${props.message ? html`<div class="alert alert-secondary mb-0">${props.message}</div>` : null}
        <div class="d-flex flex-wrap gap-2">
          <a class="btn btn-outline-primary" href=${routeHref("/wifi/scan")}>Scan Networks</a>
        </div>
        <div class="card shadow-sm border-0">
          <div class="card-body p-4">
            <h2 class="h5 mb-1">Saved Networks</h2>
            <p class="text-body-secondary mb-0">Priority order decides what the Pico tries first on boot.</p>
            ${props.profiles.length
              ? html`
                  <div class="d-grid gap-3 mt-3">
                    ${props.profiles.map(function (profile, index) {
                      return html`
                        <div key=${profile.ssid + ":" + index} class="card bg-body-tertiary border-secondary-subtle">
                          <div class="card-body py-3">
                            <div class="d-flex flex-column flex-lg-row justify-content-between align-items-start gap-3">
                              <div>
                                <div class="fw-semibold">${profile.ssid}</div>
                                <div class="small text-body-secondary mt-1">
                                  ${profile.password ? "Password saved" : "Open network"}
                                </div>
                              </div>
                              <div class="d-flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  class="btn btn-sm btn-primary"
                                  onClick=${function () {
                                    props.onConnect(profile.ssid, profile.password || "");
                                  }}
                                >
                                  Join
                                </button>
                                <button
                                  type="button"
                                  class="btn btn-sm btn-outline-secondary"
                                  onClick=${function () {
                                    props.onEdit(index);
                                  }}
                                >
                                  Edit
                                </button>
                                ${index > 0
                                  ? html`
                                      <button
                                        type="button"
                                        class="btn btn-sm btn-outline-secondary"
                                        onClick=${function () {
                                          props.onMove(index, -1);
                                        }}
                                      >
                                        Up
                                      </button>
                                    `
                                  : null}
                                ${index < props.profiles.length - 1
                                  ? html`
                                      <button
                                        type="button"
                                        class="btn btn-sm btn-outline-secondary"
                                        onClick=${function () {
                                          props.onMove(index, 1);
                                        }}
                                      >
                                        Down
                                      </button>
                                    `
                                  : null}
                                <button
                                  type="button"
                                  class="btn btn-sm btn-outline-danger"
                                  onClick=${function () {
                                    props.onDelete(index);
                                  }}
                                >
                                  Delete
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      `;
                    })}
                  </div>
                `
              : html`<div class="text-body-secondary fst-italic mt-3">No saved networks.</div>`}
          </div>
        </div>
        <div class="card shadow-sm border-0">
          <div class="card-body p-4">
            <h2 class="h5 mb-3">${props.editIndex >= 0 ? "Edit Network" : "Add Network"}</h2>
            <div class="d-grid gap-3">
              <input
                class="form-control"
                type="text"
                placeholder="SSID"
                value=${props.ssid}
                onInput=${function (event) {
                  props.onSsid(event.currentTarget.value);
                }}
              />
              <input
                class="form-control"
                type="password"
                placeholder="Password (leave blank for open network)"
                value=${props.password}
                onInput=${function (event) {
                  props.onPassword(event.currentTarget.value);
                }}
              />
              <div class="d-flex flex-wrap gap-2 justify-content-center justify-content-sm-start">
                <button class="btn btn-primary" type="button" disabled=${props.busy} onClick=${props.onSave}>
                  ${props.editIndex >= 0 ? "Update Network" : "Save Network"}
                </button>
                ${props.editIndex >= 0
                  ? html`
                      <button class="btn btn-outline-secondary" type="button" disabled=${props.busy} onClick=${props.onCancel}>
                        Cancel
                      </button>
                    `
                  : null}
              </div>
              <div class="form-text">
                Save networks here, then use Join from the saved list when needed.
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function WifiScanView(props) {
    return html`
      <div class="d-grid gap-3">
        <div class="card shadow-sm border-0">
          <div class="card-body p-4">
            <h2 class="h5 mb-3">Current Connection</h2>
            <${WifiCurrentCard} current=${props.current} />
          </div>
        </div>
        ${props.message ? html`<div class="alert alert-secondary mb-0">${props.message}</div>` : null}
        <div class="d-flex flex-wrap gap-2">
          <a class="btn btn-outline-primary" href=${routeHref("/wifi")}>Saved Networks</a>
          <button class="btn btn-outline-secondary" onClick=${props.onScan} disabled=${props.busy}>
            ${props.busy ? "Scanning..." : "Rescan"}
          </button>
        </div>
        ${props.error ? html`<div class="alert alert-danger mb-0">${props.error}</div>` : null}
        <div class="card shadow-sm border-0">
          <div class="card-body p-4">
            <h2 class="h5 mb-3">Available Networks</h2>
            ${props.networks.length
              ? html`
                  <div class="d-grid gap-3">
                    ${props.networks.map(function (network, index) {
                      var showForm = !!props.open[index];
                      return html`
                        <div key=${network.ssid + ":" + index} class="card bg-body-tertiary border-secondary-subtle">
                          <div class="card-body py-3">
                            <div class="d-flex flex-column flex-lg-row justify-content-between align-items-start gap-3">
                              <div>
                                <div class="fw-semibold">${network.ssid}</div>
                                <div class="d-flex flex-wrap align-items-center gap-2 small text-body-secondary mt-1">
                                  <span>${network.rssi} dBm</span>
                                  ${network.saved
                                    ? html`<span class="badge rounded-pill text-bg-secondary">Saved</span>`
                                    : null}
                                  <span
                                    class=${"badge rounded-pill " + (network.secure ? "text-bg-warning" : "text-bg-success")}
                                  >
                                    ${network.secure ? "Secured" : "Open"}
                                  </span>
                                </div>
                              </div>
                              <button
                                type="button"
                                class=${"btn btn-sm " + (network.secure ? "btn-primary" : "btn-outline-primary")}
                                onClick=${function () {
                                  props.onToggle(index);
                                }}
                              >
                                ${network.secure ? "Join" : "Join Open"}
                              </button>
                            </div>
                            ${network.secure && showForm
                              ? html`
                                  <div class="row g-2 mt-2">
                                    <div class="col-12 col-md">
                                      <input
                                        class="form-control"
                                        type="password"
                                        placeholder="Password"
                                        value=${props.passwords[index] || ""}
                                        onInput=${function (event) {
                                          props.onPassword(index, event.currentTarget.value);
                                        }}
                                      />
                                    </div>
                                    <div class="col-12 col-md-auto">
                                      <button
                                        type="button"
                                        class="btn btn-primary w-100"
                                        onClick=${function () {
                                          props.onConnect(index);
                                        }}
                                      >
                                        Connect
                                      </button>
                                    </div>
                                  </div>
                                `
                              : null}
                          </div>
                        </div>
                      `;
                    })}
                  </div>
                `
              : html`
                  <div class="text-body-secondary fst-italic">
                    ${props.busy ? "Scanning..." : "No networks found."}
                  </div>
                `}
          </div>
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
    var [touchActive, setTouchActive] = useState(false);
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
      var timer = setInterval(refreshSysinfo, 1000);
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

    function setTouchMode(active) {
      if (!active) {
        setTouchActive(false);
      }
      return postPlain("/api/led/touch-mode?active=" + (active ? 1 : 0), "")
        .catch(function () {
          setTouchActive(false);
          setBootError("Touch pad mode update failed.");
        });
    }

    function setTouchPressed(pressed) {
      var next = !!pressed;
      if (next === touchActive) {
        return Promise.resolve();
      }
      setTouchActive(next);
      return postPlain("/api/led/touch?state=" + (next ? 1 : 0), "")
        .catch(function () {
          setTouchActive(false);
          setBootError("Touch pad update failed.");
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
      content = html`
        <div class="card shadow-sm border-0">
          <div class="card-body p-4 text-body-secondary fst-italic text-center">Loading device state...</div>
        </div>
      `;
    } else if (route === "/") {
      content = html`<${HomeView} patternNames=${patternNames} />`;
    } else if (route === "/led") {
      content = html`<${LedView} patternNames=${patternNames} ledMode=${ledMode} onPick=${selectLed} />`;
    } else if (route === "/touch") {
      content = html`<${TouchPadView} active=${touchActive} onMode=${setTouchMode} onPress=${setTouchPressed} />`;
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
      <div class="container py-4 py-sm-5">
        <div class="row justify-content-center">
          <div class="col-12 col-lg-8 col-xl-7">
            <div class="d-grid gap-3">
              <${Header} route=${route} onHome=${goHome} />
              ${bootError ? html`<div class="alert alert-danger mb-0">${bootError}</div>` : null}
              ${content}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  var root = document.getElementById("app");
  if (!root) {
    return;
  }
  root.className = "min-vh-100";
  root.textContent = "";
  render(html`<${App} />`, root);
  window.__pico_app_started = true;
})();
