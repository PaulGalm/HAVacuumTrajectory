class VacuumPathCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) {
      throw new Error("Entity is required");
    }
    this._config = {
      line_color: "#1e88e5",
      point_color: "#ef5350",
      line_width: 2,
      show_points: true,
      background: "#0d1117",
      ...config,
    };
    if (!this.content) {
      this.content = document.createElement("ha-card");
      this.canvas = document.createElement("canvas");
      this.canvas.style.width = "100%";
      this.canvas.style.height = "300px";
      this.content.appendChild(this.canvas);
      this.appendChild(this.content);
    }
    if (this._hass) {
      this._update();
    }
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  _update() {
    if (!this.canvas || !this._config || !this._hass) {
      return;
    }
    const stateObj = this._hass.states[this._config.entity];
    if (!stateObj) {
      this._drawEmpty("Entity not found");
      return;
    }
    const history = stateObj.attributes.history;
    if (!Array.isArray(history) || history.length === 0) {
      this._drawEmpty("No data");
      return;
    }

    const ctx = this.canvas.getContext("2d");
    const pixelRatio = window.devicePixelRatio || 1;
    const width = this.canvas.clientWidth || this.canvas.parentElement.offsetWidth;
    const height = this.canvas.clientHeight || 300;
    if (this.canvas.width !== Math.floor(width * pixelRatio)) {
      this.canvas.width = Math.floor(width * pixelRatio);
    }
    if (this.canvas.height !== Math.floor(height * pixelRatio)) {
      this.canvas.height = Math.floor(height * pixelRatio);
    }
    ctx.resetTransform?.();
    ctx.scale(pixelRatio, pixelRatio);
    ctx.fillStyle = this._config.background;
    ctx.fillRect(0, 0, width, height);

    const xs = history.map((p) => Number(p.x)).filter((v) => !Number.isNaN(v));
    const ys = history.map((p) => Number(p.y)).filter((v) => !Number.isNaN(v));
    if (xs.length === 0 || ys.length === 0) {
      this._drawEmpty("Invalid coordinates");
      return;
    }

    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const padding = 20;
    const scaleX = (maxX - minX) === 0 ? 1 : (width - padding * 2) / (maxX - minX);
    const scaleY = (maxY - minY) === 0 ? 1 : (height - padding * 2) / (maxY - minY);

    const toCanvas = (point) => {
      const x = padding + (Number(point.x) - minX) * scaleX;
      const y = height - padding - (Number(point.y) - minY) * scaleY;
      return { x, y };
    };

    ctx.lineWidth = this._config.line_width;
    ctx.strokeStyle = this._config.line_color;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    history.forEach((point, index) => {
      const { x, y } = toCanvas(point);
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    if (this._config.show_points) {
      ctx.fillStyle = this._config.point_color;
      history.forEach((point) => {
        const { x, y } = toCanvas(point);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    }
  }

  _drawEmpty(message) {
    if (!this.canvas) {
      return;
    }
    const pixelRatio = window.devicePixelRatio || 1;
    const width = this.canvas.clientWidth || this.canvas.parentElement?.offsetWidth || 600;
    const height = this.canvas.clientHeight || 300;
    if (this.canvas.width !== Math.floor(width * pixelRatio)) {
      this.canvas.width = Math.floor(width * pixelRatio);
    }
    if (this.canvas.height !== Math.floor(height * pixelRatio)) {
      this.canvas.height = Math.floor(height * pixelRatio);
    }
    const ctx = this.canvas.getContext("2d");
    ctx.resetTransform?.();
    ctx.scale(pixelRatio, pixelRatio);
    ctx.fillStyle = this._config ? this._config.background : "#111";
    ctx.fillRect(0, 0, width, height);
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "16px sans-serif";
    ctx.fillText(message, width / 2, height / 2);
  }

  getCardSize() {
    return 3;
  }
}

customElements.define("vacuum-path-card", VacuumPathCard);
