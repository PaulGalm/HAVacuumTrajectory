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
      background_image: null,
      scale: 1,
      rotation: 0,
      offset_x: 0,
      offset_y: 0,
      invert_y: true,
      ...config,
    };
    this._image = this._image || null;
    this._imageSrc = this._imageSrc || null;
    this._imageLoading = Boolean(this._imageLoading);
    this._imageErrorSrc = null;

    if (!this.content) {
      this.content = document.createElement("ha-card");
      this.canvas = document.createElement("canvas");
      this.canvas.style.width = "100%";
      this.canvas.style.height = "300px";
      this.content.appendChild(this.canvas);
      this.appendChild(this.content);
    }

    this._ensureImage();
    if (this._hass) {
      this._update();
    }
  }

  static getStubConfig() {
    return {
      entity: "",
      line_color: "#1e88e5",
      point_color: "#ef5350",
      line_width: 2,
      show_points: true,
      background: "#0d1117",
    };
  }

  getConfigElement() {
    return document.createElement("vacuum-path-card-editor");
  }

  getCardSize() {
    return 3;
  }

  set hass(hass) {
    this._hass = hass;
    this._ensureImage();
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

    this._ensureImage();
    const imageReady = this._isImageReady();

    const displayWidth =
      this.canvas.clientWidth || this.canvas.parentElement?.offsetWidth || 600;
    let displayHeight = this.canvas.clientHeight || 300;
    if (imageReady) {
      const aspect = this._image.naturalHeight / this._image.naturalWidth;
      displayHeight = displayWidth * aspect;
    }

    this.canvas.style.height = `${displayHeight}px`;

    const pixelRatio = window.devicePixelRatio || 1;
    const targetWidth = Math.floor(displayWidth * pixelRatio);
    const targetHeight = Math.floor(displayHeight * pixelRatio);
    if (this.canvas.width !== targetWidth) {
      this.canvas.width = targetWidth;
    }
    if (this.canvas.height !== targetHeight) {
      this.canvas.height = targetHeight;
    }

    const ctx = this.canvas.getContext("2d");
    ctx.resetTransform?.();
    ctx.scale(pixelRatio, pixelRatio);
    ctx.fillStyle = this._config.background;
    ctx.fillRect(0, 0, displayWidth, displayHeight);
    if (imageReady) {
      ctx.drawImage(this._image, 0, 0, displayWidth, displayHeight);
    }

    const transformed = history
      .map((point) => this._transformPoint(point))
      .filter((p) => p !== null);

    if (transformed.length === 0) {
      this._drawEmpty("Invalid coordinates");
      return;
    }

    const invertY = this._config.invert_y !== false;
    let toCanvas;
    if (imageReady) {
      const scaleX = displayWidth / this._image.naturalWidth;
      const scaleY = displayHeight / this._image.naturalHeight;
      toCanvas = (point) => {
        const x = point.x * scaleX;
        const y = invertY
          ? displayHeight - point.y * scaleY
          : point.y * scaleY;
        return { x, y };
      };
    } else {
      const xs = transformed.map((p) => p.x);
      const ys = transformed.map((p) => p.y);
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs);
      const minY = Math.min(...ys);
      const maxY = Math.max(...ys);
      const padding = 20;
      const rangeX = maxX - minX || 1;
      const rangeY = maxY - minY || 1;
      const scaleX = (displayWidth - padding * 2) / rangeX;
      const scaleY = (displayHeight - padding * 2) / rangeY;
      toCanvas = (point) => {
        const x = padding + (point.x - minX) * scaleX;
        const y = invertY
          ? displayHeight - padding - (point.y - minY) * scaleY
          : padding + (point.y - minY) * scaleY;
        return { x, y };
      };
    }

    ctx.lineWidth = this._config.line_width;
    ctx.strokeStyle = this._config.line_color;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.beginPath();
    transformed.forEach((point, index) => {
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
      transformed.forEach((point) => {
        const { x, y } = toCanvas(point);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fill();
      });
    }
  }

  _drawEmpty(message) {
    if (!this.canvas || !this._config) {
      return;
    }
    this._ensureImage();

    const pixelRatio = window.devicePixelRatio || 1;
    const width =
      this.canvas.clientWidth || this.canvas.parentElement?.offsetWidth || 600;
    let height = this.canvas.clientHeight || 300;
    const imageReady = this._isImageReady();
    if (imageReady) {
      height = width * (this._image.naturalHeight / this._image.naturalWidth);
    }

    if (this.canvas.width !== Math.floor(width * pixelRatio)) {
      this.canvas.width = Math.floor(width * pixelRatio);
    }
    if (this.canvas.height !== Math.floor(height * pixelRatio)) {
      this.canvas.height = Math.floor(height * pixelRatio);
    }

    const ctx = this.canvas.getContext("2d");
    ctx.resetTransform?.();
    ctx.scale(pixelRatio, pixelRatio);
    ctx.fillStyle = this._config.background;
    ctx.fillRect(0, 0, width, height);
    if (imageReady) {
      ctx.drawImage(this._image, 0, 0, width, height);
    }
    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "16px sans-serif";
    ctx.fillText(message, width / 2, height / 2);
  }

  _ensureImage() {
    const src = this._config?.background_image;
    if (!src) {
      this._image = null;
      this._imageSrc = null;
      this._imageLoading = false;
      this._imageErrorSrc = null;
      return;
    }
    if (!this._hass && !src.startsWith("http")) {
      // Wait until hass is set so we can resolve /local URLs correctly.
      return;
    }
    const resolvedSrc = this._resolveResource(src);
    if (this._imageSrc === resolvedSrc) {
      if (this._image && this._image.complete) {
        return;
      }
      if (this._imageLoading) {
        return;
      }
      if (this._imageErrorSrc === resolvedSrc) {
        return;
      }
    }

    this._imageLoading = true;
    this._image = null;
    this._imageSrc = resolvedSrc;
    const img = new Image();
    img.decoding = "async";
    if (!resolvedSrc.startsWith(window.location.origin)) {
      img.crossOrigin = "anonymous";
    }
    img.onload = () => {
      this._image = img;
      this._imageLoading = false;
      this._imageErrorSrc = null;
      this._update();
    };
    img.onerror = () => {
      // eslint-disable-next-line no-console
      console.error(`Failed to load vacuum path background image: ${resolvedSrc}`);
      this._image = null;
      this._imageLoading = false;
      this._imageErrorSrc = resolvedSrc;
      this._drawEmpty("Image load error");
    };
    img.src = resolvedSrc;
  }

  _transformPoint(point) {
    const xRaw = Number(point.x);
    const yRaw = Number(point.y);
    if (Number.isNaN(xRaw) || Number.isNaN(yRaw)) {
      return null;
    }
    const offsetX = Number(this._config.offset_x) || 0;
    const offsetY = Number(this._config.offset_y) || 0;
    const scale = Number(this._config.scale) || 1;
    const rotation = Number(this._config.rotation) || 0;
    const radians = (rotation * Math.PI) / 180;
    const cos = Math.cos(radians);
    const sin = Math.sin(radians);
    const shiftedX = (xRaw + offsetX) * scale;
    const shiftedY = (yRaw + offsetY) * scale;
    const rotatedX = shiftedX * cos - shiftedY * sin;
    const rotatedY = shiftedX * sin + shiftedY * cos;
    return { x: rotatedX, y: rotatedY, timestamp: point.timestamp };
  }

  _isImageReady() {
    return Boolean(
      this._image && this._image.complete && this._image.naturalWidth > 0,
    );
  }

  _resolveResource(url) {
    if (!url) {
      return undefined;
    }
    if (this._hass && typeof this._hass.hassUrl === "function") {
      try {
        return this._hass.hassUrl(url);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("vacuum-path-card: hassUrl resolution failed", url, err);
      }
    }

    if (url.startsWith("http://") || url.startsWith("https://")) {
      return url;
    }

    if (url.startsWith("/")) {
      return `${window.location.origin}${url}`;
    }

    const base = window.location.href.split("?")[0];
    try {
      return new URL(url, base).href;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn("vacuum-path-card: unable to resolve image URL", url, err);
      return url;
    }
  }
}

customElements.define("vacuum-path-card", VacuumPathCard);
