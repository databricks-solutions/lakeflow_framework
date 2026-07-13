/**
 * Lakeflow Mermaid: lf-arch styling, inline render (no shadow DOM), click-to-expand modal.
 *
 * Diagram source lives in a sibling <template class="lf-mermaid-source"> (build time).
 * Pre tags use class lf-mermaid-src so sphinx-immaterial does not intercept them.
 */
(function () {
  "use strict";

  const ENHANCED_ATTR = "data-lf-mermaid-enhanced";
  const RENDERED_ATTR = "data-lf-mermaid-rendered";
  const PENDING_ATTR = "data-lf-mermaid-pending";
  const RENDERING_ATTR = "data-lf-mermaid-rendering";

  let mermaidReadyPromise = null;
  let renderCounter = 0;
  let activeColorScheme = null;

  const LF_MERMAID_THEME_CSS =
    ".lf-mermaid-svg .node circle,.lf-mermaid-svg .node ellipse,.lf-mermaid-svg .node path," +
    ".lf-mermaid-svg .node polygon,.lf-mermaid-svg .node rect{" +
    "fill:var(--lf-mermaid-card-bg)!important;stroke:var(--lf-mermaid-fw)!important;" +
    "stroke-width:2px!important;rx:8px;ry:8px}" +
    ".lf-mermaid-svg .label,.lf-mermaid-svg .label span,.lf-mermaid-svg .nodeLabel," +
    ".lf-mermaid-svg .nodeLabel p,.lf-mermaid-svg .label div{color:var(--lf-mermaid-fg)!important;" +
    "fill:var(--lf-mermaid-fg)!important;font-family:var(--md-text-font,'Roboto'),sans-serif}" +
    ".lf-mermaid-svg .label div .edgeLabel{color:var(--lf-mermaid-muted)!important;" +
    "fill:var(--lf-mermaid-muted)!important;font-size:0.82em}" +
    ".lf-mermaid-svg .edgeLabel,.lf-mermaid-svg .edgeLabel p{" +
    "fill:var(--lf-mermaid-card-bg)!important;color:var(--lf-mermaid-muted)!important;" +
    "background-color:var(--lf-mermaid-card-bg)!important}" +
    ".lf-mermaid-svg .edgeLabel rect{fill:var(--lf-mermaid-card-bg)!important;stroke:none!important}" +
    ".lf-mermaid-svg .edgePath .path,.lf-mermaid-svg .flowchart-link{" +
    "stroke:var(--lf-mermaid-edge)!important;stroke-width:2px!important}" +
    ".lf-mermaid-svg .edgePath .arrowheadPath,.lf-mermaid-svg marker path," +
    ".lf-mermaid-svg marker polygon{fill:var(--lf-mermaid-edge)!important;stroke:none!important}" +
    ".lf-mermaid-svg .cluster rect{" +
    "fill:var(--lf-mermaid-fw-panel)!important;stroke:var(--lf-mermaid-fw)!important;" +
    "stroke-width:2.75px!important;rx:12px;ry:12px}" +
    ".lf-mermaid-svg .cluster-label,.lf-mermaid-svg .cluster-label span," +
    ".lf-mermaid-svg .cluster .label text,.lf-mermaid-svg .cluster .label span{" +
    "fill:var(--lf-mermaid-fg)!important;color:var(--lf-mermaid-fg)!important;" +
    "font-weight:700!important;font-family:var(--md-text-font,'Roboto'),sans-serif}";

  function getColorScheme() {
    const scheme = document.body.getAttribute("data-md-color-scheme");
    return scheme === "slate" ? "slate" : "default";
  }

  function getMermaidSource(container) {
    const template = container.querySelector("template.lf-mermaid-source");
    if (template) {
      return template.content.textContent.trim();
    }
    const pre = container.querySelector("pre.lf-mermaid-src, pre.mermaid");
    if (pre) {
      return pre.textContent.trim();
    }
    return (container.dataset.lfMermaidSource || "").trim();
  }

  function getMermaidScriptUrl() {
    const configEl = document.getElementById("__config");
    let basePath = ".";
    if (configEl) {
      try {
        basePath = JSON.parse(configEl.textContent).base || ".";
      } catch (_err) {
        /* ignore */
      }
    }
    const normalized = basePath.endsWith("/") ? basePath : basePath + "/";
    return new URL(normalized + "_static/mermaid/mermaid.min.js", window.location.href).href;
  }

  function loadMermaidScript() {
    return new Promise(function (resolve, reject) {
      if (typeof window.mermaid !== "undefined") {
        resolve();
        return;
      }
      const existing = document.querySelector('script[data-lf-mermaid-loader="true"]');
      if (existing) {
        existing.addEventListener("load", function () { resolve(); }, { once: true });
        existing.addEventListener("error", reject, { once: true });
        return;
      }
      const script = document.createElement("script");
      script.src = getMermaidScriptUrl();
      script.async = true;
      script.setAttribute("data-lf-mermaid-loader", "true");
      script.onload = function () { resolve(); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  function getMermaidThemeVariables(scheme) {
    if (scheme === "slate") {
      return {
        background: "transparent",
        primaryColor: "#1e2629",
        primaryBorderColor: "#5dade2",
        primaryTextColor: "#e8eef0",
        secondaryColor: "rgba(93, 173, 226, 0.1)",
        tertiaryColor: "rgba(93, 173, 226, 0.22)",
        lineColor: "#5dade2",
        textColor: "#e8eef0",
        mainBkg: "#1e2629",
        nodeBorder: "#5dade2",
        clusterBkg: "rgba(93, 173, 226, 0.1)",
        clusterBorder: "#5dade2",
        titleColor: "#e8eef0",
        edgeLabelBackground: "#1e2629",
        fontFamily: "Roboto, sans-serif",
      };
    }
    return {
      background: "transparent",
      primaryColor: "#ffffff",
      primaryBorderColor: "#2b7bb9",
      primaryTextColor: "#1b3139",
      secondaryColor: "#f3f9fc",
      tertiaryColor: "#e6f2f8",
      lineColor: "#2b7bb9",
      textColor: "#1b3139",
      mainBkg: "#ffffff",
      nodeBorder: "#2b7bb9",
      clusterBkg: "#f3f9fc",
      clusterBorder: "#2b7bb9",
      titleColor: "#1b3139",
      edgeLabelBackground: "#ffffff",
      fontFamily: "Roboto, sans-serif",
    };
  }

  function ensureMermaidReady() {
    const scheme = getColorScheme();
    if (!mermaidReadyPromise || activeColorScheme !== scheme) {
      activeColorScheme = scheme;
      mermaidReadyPromise = loadMermaidScript().then(function () {
        window.mermaid.initialize({
          startOnLoad: false,
          securityLevel: "loose",
          theme: "base",
          themeVariables: getMermaidThemeVariables(scheme),
          themeCSS: LF_MERMAID_THEME_CSS,
          flowchart: {
            htmlLabels: true,
            curve: "basis",
            padding: 16,
            nodeSpacing: 42,
            rankSpacing: 52,
          },
        });
        return window.mermaid;
      });
    }
    return mermaidReadyPromise;
  }

  function resetMermaidReady() {
    mermaidReadyPromise = null;
  }

  function retagMermaidSources() {
    document.querySelectorAll(".mermaid-diagram > pre.mermaid").forEach(function (pre) {
      pre.classList.remove("mermaid");
      pre.classList.add("lf-mermaid-src");
    });
  }

  function stripInlinePresentation(svg) {
    svg.querySelectorAll(
      ".node rect, .node polygon, .node path, .cluster rect, .edgePath .path, .flowchart-link"
    ).forEach(function (el) {
      el.removeAttribute("style");
    });
  }

  function applyLfArchClasses(svg) {
    if (!svg) {
      return;
    }
    svg.classList.add("lf-mermaid-svg");
    stripInlinePresentation(svg);

    svg.querySelectorAll("g.cluster").forEach(function (cluster) {
      cluster.classList.add("lf-mermaid-cluster--fw");
    });

    svg.querySelectorAll("g.node").forEach(function (node) {
      node.classList.add("lf-mermaid-node--fw");
    });
  }

  function renderStyledDiagram(mermaid, source) {
    const renderId = "lf-mermaid-" + (++renderCounter);
    return mermaid.render(renderId, source).then(function (result) {
      const host = document.createElement("div");
      host.className = "lf-mermaid-rendered";
      host.innerHTML = result.svg;
      const svg = host.querySelector("svg");
      applyLfArchClasses(svg);
      if (typeof result.bindFunctions === "function") {
        result.bindFunctions(host);
      }
      return host;
    });
  }

  function isRendered(container) {
    return !!container.querySelector(".lf-mermaid-rendered, div.mermaid");
  }

  function renderInline(container) {
    if (container.getAttribute(RENDERING_ATTR) === "true") {
      return Promise.resolve(false);
    }
    if (isRendered(container)) {
      return Promise.resolve(true);
    }

    const source = getMermaidSource(container);
    const pre = container.querySelector("pre.lf-mermaid-src, pre.mermaid");
    if (!source || !pre) {
      return Promise.resolve(false);
    }

    container.setAttribute(RENDERING_ATTR, "true");
    container.removeAttribute(PENDING_ATTR);

    return ensureMermaidReady()
      .then(function (mermaid) {
        return renderStyledDiagram(mermaid, source);
      })
      .then(function (host) {
        container.classList.add("lf-mermaid");
        pre.replaceWith(host);
        container.setAttribute(RENDERED_ATTR, "true");
        container.dataset.lfMermaidSource = source;
        return true;
      })
      .catch(function (err) {
        container.removeAttribute(PENDING_ATTR);
        if (typeof console !== "undefined" && console.warn) {
          console.warn("Lakeflow Mermaid: render failed", err);
        }
        return false;
      })
      .finally(function () {
        container.removeAttribute(RENDERING_ATTR);
      });
  }

  function ensureDialog() {
    let dialog = document.getElementById("lf-mermaid-dialog");
    if (dialog) {
      return dialog;
    }

    dialog = document.createElement("dialog");
    dialog.id = "lf-mermaid-dialog";
    dialog.className = "lf-mermaid-dialog";
    dialog.innerHTML =
      '<div class="lf-mermaid-dialog__header">' +
      '<span class="lf-mermaid-dialog__title">Diagram</span>' +
      '<div class="lf-mermaid-dialog__tools">' +
      '<button type="button" class="lf-mermaid-dialog__btn" data-zoom="out" aria-label="Zoom out">−</button>' +
      '<button type="button" class="lf-mermaid-dialog__btn" data-zoom="reset" aria-label="Reset zoom">Reset</button>' +
      '<button type="button" class="lf-mermaid-dialog__btn" data-zoom="in" aria-label="Zoom in">+</button>' +
      '<button type="button" class="lf-mermaid-dialog__btn lf-mermaid-dialog__close" aria-label="Close">Close</button>' +
      "</div></div>" +
      '<div class="lf-mermaid-dialog__stage" tabindex="0">' +
      '<div class="lf-mermaid-dialog__canvas lf-mermaid"></div>' +
      "</div>" +
      '<p class="lf-mermaid-dialog__hint">Scroll or pinch to zoom · drag to pan · Esc to close</p>';

    document.body.appendChild(dialog);
    return dialog;
  }

  function enhanceContainer(container) {
    if (container.getAttribute(ENHANCED_ATTR) === "true") {
      return false;
    }

    const source = getMermaidSource(container);
    if (!source || !isRendered(container)) {
      container.setAttribute(PENDING_ATTR, "true");
      return false;
    }

    container.removeAttribute(PENDING_ATTR);
    container.dataset.lfMermaidSource = source;

    if (container.closest(".lf-mermaid-shell")) {
      container.setAttribute(ENHANCED_ATTR, "true");
      return true;
    }

    const shell = document.createElement("div");
    shell.className = "lf-mermaid-shell lf-mermaid";

    const parent = container.parentNode;
    parent.insertBefore(shell, container);
    shell.appendChild(container);

    const hint = document.createElement("p");
    hint.className = "lf-mermaid-hint";
    hint.textContent = "Click diagram to expand · scroll to zoom · drag to pan";
    shell.appendChild(hint);

    shell.addEventListener("click", function (event) {
      if (event.target.closest(".lf-mermaid-hint")) {
        return;
      }
      openDialog(container);
    });

    container.setAttribute(ENHANCED_ATTR, "true");
    return true;
  }

  function openDialog(container) {
    const source = getMermaidSource(container);
    if (!source) {
      return;
    }

    const dialog = ensureDialog();
    const canvas = dialog.querySelector(".lf-mermaid-dialog__canvas");
    const stage = dialog.querySelector(".lf-mermaid-dialog__stage");
    if (!canvas || !stage) {
      return;
    }

    canvas.innerHTML = '<p class="lf-mermaid-dialog__loading">Loading diagram…</p>';

    let scale = 1;
    let panX = 0;
    let panY = 0;
    let dragging = false;
    let lastX = 0;
    let lastY = 0;

    function applyTransform() {
      canvas.style.transform = "translate(" + panX + "px, " + panY + "px) scale(" + scale + ")";
    }

    function resetView() {
      scale = 1;
      panX = 0;
      panY = 0;
      applyTransform();
    }

    function zoomBy(delta) {
      scale = Math.min(4, Math.max(0.35, scale + delta));
      applyTransform();
    }

    function onWheel(event) {
      event.preventDefault();
      zoomBy(event.deltaY < 0 ? 0.12 : -0.12);
    }

    function onPointerDown(event) {
      if (event.button !== 0) {
        return;
      }
      dragging = true;
      lastX = event.clientX;
      lastY = event.clientY;
      stage.setPointerCapture(event.pointerId);
      stage.classList.add("lf-mermaid-dialog__stage--dragging");
    }

    function onPointerMove(event) {
      if (!dragging) {
        return;
      }
      panX += event.clientX - lastX;
      panY += event.clientY - lastY;
      lastX = event.clientX;
      lastY = event.clientY;
      applyTransform();
    }

    function onPointerUp(event) {
      dragging = false;
      stage.classList.remove("lf-mermaid-dialog__stage--dragging");
      try {
        stage.releasePointerCapture(event.pointerId);
      } catch (_err) {
        /* ignore */
      }
    }

    function onDialogClick(event) {
      const action = event.target.closest("[data-zoom]");
      if (!action) {
        return;
      }
      const mode = action.getAttribute("data-zoom");
      if (mode === "in") {
        zoomBy(0.2);
      } else if (mode === "out") {
        zoomBy(-0.2);
      } else if (mode === "reset") {
        resetView();
      }
    }

    function onClose() {
      stage.removeEventListener("wheel", onWheel);
      stage.removeEventListener("pointerdown", onPointerDown);
      stage.removeEventListener("pointermove", onPointerMove);
      stage.removeEventListener("pointerup", onPointerUp);
      stage.removeEventListener("pointercancel", onPointerUp);
      dialog.removeEventListener("click", onDialogClick);
      dialog.removeEventListener("close", onClose);
      canvas.innerHTML = "";
    }

    stage.addEventListener("wheel", onWheel, { passive: false });
    stage.addEventListener("pointerdown", onPointerDown);
    stage.addEventListener("pointermove", onPointerMove);
    stage.addEventListener("pointerup", onPointerUp);
    stage.addEventListener("pointercancel", onPointerUp);
    dialog.addEventListener("click", onDialogClick);
    dialog.addEventListener("close", onClose);

    dialog.querySelector(".lf-mermaid-dialog__close").onclick = function () {
      dialog.close();
    };

    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "open");
    }

    ensureMermaidReady()
      .then(function (mermaid) {
        return renderStyledDiagram(mermaid, source);
      })
      .then(function (host) {
        canvas.innerHTML = "";
        canvas.appendChild(host);
        resetView();
      })
      .catch(function () {
        canvas.innerHTML = '<p class="lf-mermaid-dialog__loading">Could not render diagram.</p>';
      });
  }

  function rerenderAll() {
    const hasRendered = document.querySelector(".lf-mermaid-rendered");
    resetMermaidReady();
    if (!hasRendered) {
      scan();
      return;
    }
    document.querySelectorAll(".md-typeset .mermaid-diagram").forEach(function (container) {
      const source = getMermaidSource(container);
      const rendered = container.querySelector(".lf-mermaid-rendered");
      if (!source || !rendered) {
        return;
      }
      ensureMermaidReady()
        .then(function (mermaid) {
          return renderStyledDiagram(mermaid, source);
        })
        .then(function (host) {
          rendered.replaceWith(host);
        })
        .catch(function () {
          /* keep existing render on failure */
        });
    });
  }

  function processContainer(container) {
    return renderInline(container).then(function (rendered) {
      if (rendered || isRendered(container)) {
        enhanceContainer(container);
      }
      return rendered;
    });
  }

  function scan() {
    const containers = Array.from(document.querySelectorAll(".md-typeset .mermaid-diagram"));
    let pending = false;

    containers.forEach(function (container) {
      if (container.getAttribute(ENHANCED_ATTR) === "true" && isRendered(container)) {
        return;
      }
      if (container.getAttribute(RENDERING_ATTR) === "true") {
        pending = true;
        return;
      }
      if (!isRendered(container) && getMermaidSource(container)) {
        pending = true;
        processContainer(container);
      } else if (isRendered(container)) {
        enhanceContainer(container);
      }
    });

    return pending;
  }

  function boot() {
    retagMermaidSources();

    let attempts = 0;
    const maxAttempts = 120;

    function tick() {
      const pending = scan();
      attempts += 1;
      if (pending && attempts < maxAttempts) {
        window.setTimeout(tick, 250);
      }
    }

    tick();

    const observer = new MutationObserver(function () {
      retagMermaidSources();
      scan();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    const main = document.querySelector(".md-content__inner");
    if (main) {
      observer.observe(main, { childList: true, subtree: true });
    }

    const schemeObserver = new MutationObserver(function () {
      const scheme = getColorScheme();
      if (scheme !== activeColorScheme) {
        rerenderAll();
      }
    });
    schemeObserver.observe(document.body, {
      attributes: true,
      attributeFilter: ["data-md-color-scheme"],
    });
  }

  retagMermaidSources();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
