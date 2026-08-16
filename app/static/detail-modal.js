/* 详情弹窗：点击「查看译注 / 字词 / 导读」→ 拉取 /api/book/{name}/detail/{id} 并在弹窗内渲染。
 * 不离开当前阅读页，也不直接展示原始 JSON。
 */
(function () {
  "use strict";

  // 详情字段 → 标签页定义（按顺序）。只渲染有内容的字段。
  var SECTIONS = [
    { key: "translate_text", label: "译注" },
    { key: "word_explain", label: "字词" },
    { key: "intro_reading", label: "导读" },
    { key: "extended_reading", label: "拓展阅读" },
    { key: "story", label: "故事" }
  ];

  var overlay, modal, closeBtn, head, tabsEl, contentEl;
  var currentData = null;
  var currentTab = null;

  function ensureModal() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.className = "rb-modal-overlay";
    overlay.id = "rbModalOverlay";
    overlay.innerHTML =
      '<div class="rb-modal" role="dialog" aria-modal="true">' +
        '<button class="rb-modal-close" type="button" aria-label="关闭">&times;</button>' +
        '<div class="rb-modal-head"><div class="rb-original"></div><div class="rb-pinyin"></div></div>' +
        '<div class="rb-tabs"></div>' +
        '<div class="rb-tab-content"></div>' +
      "</div>";
    document.body.appendChild(overlay);

    modal = overlay.querySelector(".rb-modal");
    closeBtn = overlay.querySelector(".rb-modal-close");
    head = overlay.querySelector(".rb-modal-head");
    tabsEl = overlay.querySelector(".rb-tabs");
    contentEl = overlay.querySelector(".rb-tab-content");

    closeBtn.addEventListener("click", closeModal);
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeModal();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && overlay.classList.contains("open")) closeModal();
    });

    tabsEl.addEventListener("click", function (e) {
      var btn = e.target.closest(".rb-tab");
      if (!btn) return;
      selectTab(btn.getAttribute("data-key"));
    });
  }

  function openModal() {
    ensureModal();
    overlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    if (!overlay) return;
    overlay.classList.remove("open");
    document.body.style.overflow = "";
  }

  function renderLoading() {
    tabsEl.innerHTML = "";
    contentEl.className = "rb-tab-content rb-loading";
    contentEl.textContent = "加载中…";
  }

  function renderError(msg) {
    tabsEl.innerHTML = "";
    contentEl.className = "rb-tab-content rb-error";
    contentEl.textContent = "加载失败：" + msg;
  }

  function selectTab(key) {
    currentTab = key;
    var buttons = tabsEl.querySelectorAll(".rb-tab");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].classList.toggle("active", buttons[i].getAttribute("data-key") === key);
    }
    contentEl.className = "rb-tab-content";
    contentEl.textContent = (currentData[key] || "").trim() || "（暂无内容）";
  }

  function renderData(data) {
    currentData = data;
    head.querySelector(".rb-original").textContent = data.original || "";
    head.querySelector(".rb-pinyin").textContent = data.pinyin || "";

    var available = SECTIONS.filter(function (s) {
      return data[s.key] && String(data[s.key]).trim().length > 0;
    });

    if (available.length === 0) {
      tabsEl.innerHTML = "";
      contentEl.className = "rb-tab-content";
      contentEl.textContent = "（本句暂无译注/字词/导读内容）";
      return;
    }

    tabsEl.innerHTML = available
      .map(function (s) {
        return '<button type="button" class="rb-tab" data-key="' + s.key + '">' + s.label + "</button>";
      })
      .join("");

    selectTab(available[0].key);
  }

  function loadDetail(url) {
    openModal();
    renderLoading();
    fetch(url, { headers: { Accept: "application/json" } })
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.json();
      })
      .then(function (data) {
        renderData(data);
      })
      .catch(function (err) {
        renderError(err.message || "网络错误");
      });
  }

  function init() {
    var links = document.querySelectorAll("a.read-detail");
    for (var i = 0; i < links.length; i++) {
      links[i].addEventListener("click", function (e) {
        e.preventDefault();
        var url = this.getAttribute("data-detail-url") || this.getAttribute("href");
        if (url) loadDetail(url);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
