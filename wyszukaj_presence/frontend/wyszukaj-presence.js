class WyszukajPresencePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._devices = [];
    this._loading = false;
  }

  set hass(value) {
    const firstAssignment = this._hass === null;
    this._hass = value;
    if (firstAssignment && this.isConnected) this._loadDevices();
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    this._renderShell();
    this._loadDevices();
  }

  _renderShell() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          box-sizing: border-box;
          min-height: 100%;
          padding: 28px 20px 48px;
          color: var(--primary-text-color);
          background: var(--primary-background-color);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }
        * { box-sizing: border-box; }
        .wrap { max-width: 760px; margin: 0 auto; }
        .hero {
          display: flex;
          align-items: center;
          gap: 16px;
          margin: 4px 0 22px;
        }
        .hero-icon {
          display: grid;
          place-items: center;
          width: 52px;
          height: 52px;
          border-radius: 16px;
          background: color-mix(in srgb, var(--primary-color) 16%, transparent);
          color: var(--primary-color);
          font-size: 27px;
        }
        h1 { margin: 0; font-size: 28px; line-height: 1.2; }
        .subtitle {
          margin-top: 5px;
          color: var(--secondary-text-color);
          line-height: 1.45;
        }
        .card {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: var(--ha-card-border-radius, 16px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 10px rgba(0,0,0,.10));
          padding: 22px;
          margin-bottom: 18px;
        }
        .card-title {
          font-size: 18px;
          font-weight: 650;
          margin-bottom: 17px;
        }
        form {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
          gap: 12px;
          align-items: end;
        }
        label {
          display: grid;
          gap: 7px;
          color: var(--secondary-text-color);
          font-size: 12px;
          font-weight: 600;
        }
        input {
          width: 100%;
          height: 44px;
          padding: 0 13px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: var(--primary-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }
        input:focus {
          outline: 2px solid var(--primary-color);
          outline-offset: 1px;
          border-color: transparent;
        }
        button {
          height: 44px;
          padding: 0 20px;
          border: 0;
          border-radius: 10px;
          background: var(--primary-color);
          color: var(--text-primary-color, #fff);
          font: inherit;
          font-weight: 650;
          cursor: pointer;
        }
        button:hover { filter: brightness(1.06); }
        button:disabled { opacity: .55; cursor: default; }
        .error {
          min-height: 20px;
          padding-top: 10px;
          color: var(--error-color);
          font-size: 13px;
        }
        .info {
          display: flex;
          gap: 12px;
          align-items: flex-start;
          padding: 14px 15px;
          border-radius: 12px;
          background: color-mix(in srgb, var(--primary-color) 9%, transparent);
          color: var(--secondary-text-color);
          font-size: 13px;
          line-height: 1.5;
          margin-top: 4px;
        }
        .info strong { color: var(--primary-text-color); }
        .devices { display: grid; gap: 10px; }
        .device {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          padding: 13px 14px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--primary-background-color);
        }
        .device-name { font-weight: 650; margin-bottom: 4px; }
        .mac {
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          color: var(--secondary-text-color);
          font-size: 12px;
        }
        .badge {
          flex: 0 0 auto;
          padding: 5px 9px;
          border-radius: 999px;
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
          color: var(--primary-color);
          font-size: 11px;
          font-weight: 700;
        }
        .empty { color: var(--secondary-text-color); font-size: 14px; }
        @media (max-width: 680px) {
          :host { padding: 18px 12px 36px; }
          .card { padding: 17px; }
          form { grid-template-columns: 1fr; }
          button { width: 100%; }
        }
      </style>

      <div class="wrap">
        <div class="hero">
          <div class="hero-icon">⌂</div>
          <div>
            <h1>Urządzenia obecności</h1>
            <div class="subtitle">Tutaj tylko dodajesz urządzenia. Ich status możesz pokazać na głównym pulpicie Home Assistant.</div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Dodaj urządzenie</div>
          <form id="add-form">
            <label>
              NAZWA URZĄDZENIA
              <input id="name" name="name" autocomplete="off" placeholder="np. iPhone Jan" required />
            </label>
            <label>
              ADRES MAC
              <input id="mac" name="mac" autocomplete="off" placeholder="AA:BB:CC:DD:EE:FF" required />
            </label>
            <button id="add-button" type="submit">Dodaj</button>
          </form>
          <div id="error" class="error" role="alert"></div>
          <div class="info">
            <span>●</span>
            <span>Po dodaniu Home Assistant tworzy encję obecności dla urządzenia. W <strong>Przeglądzie</strong> dodaj ją do dowolnej karty.</span>
          </div>
        </div>

        <div class="card">
          <div class="card-title">Dodane urządzenia</div>
          <div id="devices" class="devices"></div>
        </div>
      </div>
    `;

    this.shadowRoot.getElementById("add-form").addEventListener("submit", (event) => {
      event.preventDefault();
      this._addDevice();
    });
    this._renderDevices();
  }

  _escape(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _renderDevices() {
    const target = this.shadowRoot?.getElementById("devices");
    if (!target) return;

    if (!this._devices.length) {
      target.innerHTML = '<div class="empty">Nie dodano jeszcze żadnego urządzenia.</div>';
      return;
    }

    target.innerHTML = this._devices.map((device) => `
      <div class="device">
        <div>
          <div class="device-name">${this._escape(device.name)}</div>
          <div class="mac">${this._escape(device.mac)}</div>
        </div>
        <div class="badge">DODANO</div>
      </div>
    `).join("");
  }

  async _loadDevices() {
    if (!this._hass || this._loading) return;
    this._loading = true;
    try {
      const response = await this._hass.connection.sendMessagePromise({
        type: "wyszukaj_presence/get_devices",
      });
      this._devices = Array.isArray(response.devices) ? response.devices : [];
      this._setError("");
      this._renderDevices();
    } catch (error) {
      this._setError("Nie można odczytać listy urządzeń.");
    } finally {
      this._loading = false;
    }
  }

  async _addDevice() {
    if (!this._hass) return;
    const nameInput = this.shadowRoot.getElementById("name");
    const macInput = this.shadowRoot.getElementById("mac");
    const button = this.shadowRoot.getElementById("add-button");
    const name = nameInput.value.trim();
    const mac = macInput.value.trim();

    this._setError("");
    button.disabled = true;
    try {
      const response = await this._hass.connection.sendMessagePromise({
        type: "wyszukaj_presence/add_device",
        name,
        mac,
      });
      this._devices = Array.isArray(response.devices) ? response.devices : [];
      nameInput.value = "";
      macInput.value = "";
      this._renderDevices();
    } catch (error) {
      const message = error?.message || error?.error?.message;
      this._setError(message || "Nie można dodać urządzenia.");
    } finally {
      button.disabled = false;
    }
  }

  _setError(message) {
    const target = this.shadowRoot?.getElementById("error");
    if (target) target.textContent = message;
  }
}

if (!customElements.get("wyszukaj-presence-panel")) {
  customElements.define("wyszukaj-presence-panel", WyszukajPresencePanel);
}
