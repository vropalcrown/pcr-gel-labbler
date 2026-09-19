// PCR Gel Genie - Web Gel Labeler Core Application Script

(function() {
    // --- Application State ---
    let state = {
        tabs: [],
        activeTabId: null,
        clipboard: []
    };

    let tabCounter = 1;


    // --- Configuration Constants ---
    const DEFAULT_SWATCH_COLORS = ["#00FF00", "#FF0000", "#00FFFF", "#FFFF00", "#FFFFFF", "#000000"];
    const LOCAL_STORAGE_KEY = "pcr_gel_genie_session";

    // --- Drag & Drop Marquee Selection Variables ---
    let selectionBox = {
        active: false,
        startX: 0,
        startY: 0,
        currentX: 0,
        currentY: 0,
        domNode: null
    };

    // --- Drag Label Variables ---
    let dragData = {
        active: false,
        startX: 0,
        startY: 0,
        initialPositions: [] // Array of { id, x, y } for selected labels when drag starts
    };

    // --- DOM Elements Cache ---
    const elements = {
        tabBar: document.getElementById("tab-bar"),
        addTabBtn: document.getElementById("add-tab-btn"),
        headerFileInput: document.getElementById("header-file-input"),
        headerSelectAllBtn: document.getElementById("header-select-all-btn"),
        floatingSelectAllBtn: document.getElementById("floating-select-all-btn"),
        undoBtn: document.getElementById("undo-btn"),
        redoBtn: document.getElementById("redo-btn"),
        exportImgBtn: document.getElementById("export-img-btn"),
        exportPptxBtn: document.getElementById("export-pptx-btn"),
        // Mark Well Boundaries (Span Mode) Controls
        spanTierSelect: document.getElementById("span-tier-select"),
        spanPatternInput: document.getElementById("span-pattern-input"),
        spanRotationSelect: document.getElementById("span-rotation-select"),
        spanSizeInput: document.getElementById("span-size-input"),
        startSpanBtn: document.getElementById("start-span-btn"),
        spanGuideBanner: document.getElementById("span-guide-banner"),
        spanGuideText: document.getElementById("span-guide-text"),
        cancelSpanBtn: document.getElementById("cancel-span-btn"),
        // Font & Styling Controls
        fontFamilySelect: document.getElementById("font-family-select"),
        fontSizeInput: document.getElementById("font-size-input"),
        colorSwatches: document.getElementById("color-swatches"),
        alignLeftBtn: document.getElementById("align-left-btn"),
        alignCenterBtn: document.getElementById("align-center-btn"),
        alignRightBtn: document.getElementById("align-right-btn"),
        alignTopBtn: document.getElementById("align-top-btn"),
        alignMiddleBtn: document.getElementById("align-middle-btn"),
        alignBottomBtn: document.getElementById("align-bottom-btn"),
        distHorizBtn: document.getElementById("dist-horiz-btn"),
        distVertBtn: document.getElementById("dist-vert-btn"),
        selectAllBtn: document.getElementById("select-all-btn"),
        alignEverythingBtn: document.getElementById("align-everything-btn"),
        gridEnableCheck: document.getElementById("grid-enable-check"),
        gridColorSelect: document.getElementById("grid-color-select"),
        gridXSpacing: document.getElementById("grid-x-spacing"),
        gridYSpacing: document.getElementById("grid-y-spacing"),
        gridXOffset: document.getElementById("grid-x-offset"),
        gridYOffset: document.getElementById("grid-y-offset"),
        gridXSpacingVal: document.getElementById("grid-x-spacing-val"),
        gridYSpacingVal: document.getElementById("grid-y-spacing-val"),
        gridXOffsetVal: document.getElementById("grid-x-offset-val"),
        gridYOffsetVal: document.getElementById("grid-y-offset-val"),
        gridControlsContainer: document.getElementById("grid-controls-container"),
        slideTitleInput: document.getElementById("slide-title-input"),
        clearLabelsBtn: document.getElementById("clear-labels-btn"),
        uploadDropzone: document.getElementById("upload-dropzone"),
        fileUploadInput: document.getElementById("file-upload-input"),
        headerFileInput: document.getElementById("header-file-input"),
        sidebarFileInput: document.getElementById("sidebar-file-input"),
        gelImgInfo: document.getElementById("gel-img-info"),
        canvasContainer: document.getElementById("canvas-container"),
        canvasWrapper: document.getElementById("canvas-wrapper"),
        gelImageDisplay: document.getElementById("gel-image-display"),
        gridOverlaySvg: document.getElementById("grid-overlay-svg"),
        labelsLayer: document.getElementById("labels-layer"),
        canvasViewport: document.getElementById("canvas-viewport"),
        statusMessage: document.getElementById("status-message"),
        coordDisplay: document.getElementById("coord-display"),
        selectionCount: document.getElementById("selection-count"),
        // Floating canvas toolbar
        floatingCanvasToolbar: document.getElementById("floating-canvas-toolbar"),
        zoomInBtn: document.getElementById("zoom-in-btn"),
        zoomOutBtn: document.getElementById("zoom-out-btn"),
        zoomResetBtn: document.getElementById("zoom-reset-btn"),
        zoomFitBtn: document.getElementById("zoom-fit-btn"),
        // Suite Navigation
        navGelBtn: document.getElementById("nav-gel-btn"),
        navColonyBtn: document.getElementById("nav-colony-btn"),
        gelModule: document.getElementById("gel-module"),
        colonyModule: document.getElementById("colony-module"),
        gelTabBarContainer: document.getElementById("gel-tab-bar-container"),
        gelGlobalActions: document.getElementById("gel-global-actions"),
        colonyGlobalActions: document.getElementById("colony-global-actions"),
        colonyHeaderFileInput: document.getElementById("colony-header-file-input"),
        
        // Modal elements
        editLabelModal: document.getElementById("edit-label-modal"),
        editLabelText: document.getElementById("edit-label-text"),
        editLabelFont: document.getElementById("edit-label-font"),
        editLabelSize: document.getElementById("edit-label-size"),
        editLabelColor: document.getElementById("edit-label-color"),
        editLabelRotation: document.getElementById("edit-label-rotation"),
        editLabelDeleteBtn: document.getElementById("edit-label-delete-btn"),
        editLabelCancelBtn: document.getElementById("edit-label-cancel-btn"),
        editLabelSaveBtn: document.getElementById("edit-label-save-btn"),
        modalCloseBtn: document.getElementById("modal-close-btn"),

        // Colony Counter Module Elements
        colonyFileInput: document.getElementById("colony-file-input"),
        colonyFileInputBtn: document.getElementById("colony-file-input-btn"),
        colonyDropzone: document.getElementById("colony-dropzone"),
        colonyCanvasContainer: document.getElementById("colony-canvas-container"),
        colonyCanvasWrapper: document.getElementById("colony-canvas-wrapper"),
        colonyImageDisplay: document.getElementById("colony-image-display"),
        colonyDishSvg: document.getElementById("colony-dish-svg"),
        colonyMarkersLayer: document.getElementById("colony-markers-layer"),
        colonyViewport: document.getElementById("colony-viewport"),
        colonySensSlider: document.getElementById("colony-sens-slider"),
        colonySensVal: document.getElementById("colony-sens-val"),
        colonyMinRad: document.getElementById("colony-min-rad"),
        colonyMaxRad: document.getElementById("colony-max-rad"),
        colonyCircSlider: document.getElementById("colony-circ-slider"),
        colonyCircVal: document.getElementById("colony-circ-val"),
        colonyMaskDish: document.getElementById("colony-mask-dish"),
        colonyInvertMode: document.getElementById("colony-invert-mode"),
        colonyColorSelect: document.getElementById("colony-color-select"),
        colonyMarkerSize: document.getElementById("colony-marker-size"),
        colonyShowNumbers: document.getElementById("colony-show-numbers"),
        colonyVolumeInput: document.getElementById("colony-volume-input"),
        colonyDilutionSelect: document.getElementById("colony-dilution-select"),
        colonyStatCount: document.getElementById("colony-stat-count"),
        colonyStatCfu: document.getElementById("colony-stat-cfu"),
        colonyImgInfo: document.getElementById("colony-img-info"),
        colonyExportImgBtn: document.getElementById("colony-export-img-btn"),
        colonyExportCsvBtn: document.getElementById("colony-export-csv-btn")
    };

    // --- Helper functions ---

    function generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
    }

    function sanitizeHexColor(col, defaultCol = "#00FF00") {
        if (typeof col === "string" && /^#([0-9a-fA-F]{3,8})$/.test(col.trim())) {
            return col.trim();
        }
        return defaultCol;
    }

    function sanitizeText(str) {
        if (typeof str !== "string") return "";
        return str.slice(0, 500);
    }

    function sanitizeNumber(val, defaultVal, min = -Infinity, max = Infinity) {
        const num = Number(val);
        if (isNaN(num) || !isFinite(num)) return defaultVal;
        return Math.max(min, Math.min(max, num));
    }

    function sanitizeCsvCellJs(val) {
        if (val === null || val === undefined) return '""';
        const str = String(val);
        let escaped = str;
        if (str.length > 0 && ['=', '+', '-', '@', '\t', '\r'].includes(str[0])) {
            escaped = "'" + str;
        }
        if (escaped.includes('"') || escaped.includes(',') || escaped.includes('\n') || escaped.includes('\r')) {
            return `"${escaped.replace(/"/g, '""')}"`;
        }
        return escaped;
    }

    // --- Lane Pattern Parser (Supports ranges like 1-29, S111-S119, literal names, commas) ---
    const MAX_RANGE_SPAN = 500;
    const MAX_TOTAL_LABELS = 1000;

    function parseLabelPattern(pattern) {
        if (!pattern || !pattern.trim()) return [];
        const parts = pattern.split(",").map(p => p.trim()).filter(Boolean);
        const labels = [];
        
        for (const part of parts) {
            if (labels.length >= MAX_TOTAL_LABELS) break;

            if (part.includes("-")) {
                const subparts = part.split("-");
                if (subparts.length === 2) {
                    const startStr = subparts[0].trim();
                    const endStr = subparts[1].trim();
                    
                    // Case 1: Simple numeric range (e.g. 1-26 or 26-1)
                    if (/^\d+$/.test(startStr) && /^\d+$/.test(endStr)) {
                        const start = parseInt(startStr, 10);
                        let end = parseInt(endStr, 10);
                        
                        if (Math.abs(end - start) + 1 > MAX_RANGE_SPAN) {
                            end = start <= end ? start + MAX_RANGE_SPAN - 1 : start - MAX_RANGE_SPAN + 1;
                        }

                        const step = start <= end ? 1 : -1;
                        for (let n = start; step > 0 ? n <= end : n >= end; n += step) {
                            labels.push(n.toString());
                            if (labels.length >= MAX_TOTAL_LABELS) break;
                        }
                        continue;
                    }
                    
                    // Case 2: Letter-prefixed range (e.g. S111-S119 or L1-L30 or P01-P09)
                    const mStart = startStr.match(/^([a-zA-Z_]+)(\d+)$/);
                    const mEnd = endStr.match(/^([a-zA-Z_]+)(\d+)$/);
                    if (mStart && mEnd && mStart[1] === mEnd[1]) {
                        const prefix = mStart[1];
                        const startVal = parseInt(mStart[2], 10);
                        let endVal = parseInt(mEnd[2], 10);
                        
                        if (Math.abs(endVal - startVal) + 1 > MAX_RANGE_SPAN) {
                            endVal = startVal <= endVal ? startVal + MAX_RANGE_SPAN - 1 : startVal - MAX_RANGE_SPAN + 1;
                        }

                        const padLen = (startStr.startsWith(prefix + "0") || endStr.startsWith(prefix + "0"))
                            ? Math.max(mStart[2].length, mEnd[2].length) : 0;
                        const step = startVal <= endVal ? 1 : -1;
                        for (let val = startVal; step > 0 ? val <= endVal : val >= endVal; val += step) {
                            const numStr = padLen > 0 ? val.toString().padStart(padLen, "0") : val.toString();
                            labels.push(`${prefix}${numStr}`);
                            if (labels.length >= MAX_TOTAL_LABELS) break;
                        }
                        continue;
                    }
                }
            }
            labels.push(part);
        }
        return labels.slice(0, MAX_TOTAL_LABELS);
    }

    // --- Mark Well Boundaries (Span Placement) State & Engine ---
    let spanState = {
        active: false,
        firstPoint: null, // { x, y } in native image coords
        tierName: "Tier 1 (Top)",
        pattern: "Ladder, 1-29",
        rotation: 0,
        fontSize: 12
    };

    function enterSpanMode() {
        const tab = getActiveTab();
        if (!tab || !tab.imageSrc) {
            showStatus("Please load a gel image first before marking well boundaries.");
            return;
        }
        
        spanState.active = true;
        spanState.firstPoint = null;
        spanState.tierName = elements.spanTierSelect ? elements.spanTierSelect.value : "Tier 1 (Top)";
        spanState.pattern = elements.spanPatternInput ? elements.spanPatternInput.value.trim() : "Ladder, 1-29";
        spanState.rotation = elements.spanRotationSelect ? parseInt(elements.spanRotationSelect.value, 10) || 0 : 0;
        spanState.fontSize = elements.spanSizeInput ? parseInt(elements.spanSizeInput.value, 10) || 12 : 12;
        
        document.body.classList.add("span-mode-active");
        if (elements.canvasWrapper) elements.canvasWrapper.classList.add("span-mode-cursor");
        if (elements.spanGuideBanner) {
            elements.spanGuideBanner.classList.remove("hidden");
            elements.spanGuideText.innerHTML = `Span Mode: Click the <strong>leftmost well</strong> (1st boundary point) for ${spanState.tierName}`;
        }
        
        clearSpanPreviewSvg();
        showStatus(`Span Mode Active: Click the leftmost well for ${spanState.tierName}`);
    }

    function cancelSpanMode() {
        if (!spanState.active) return;
        spanState.active = false;
        spanState.firstPoint = null;
        
        document.body.classList.remove("span-mode-active");
        if (elements.canvasWrapper) elements.canvasWrapper.classList.remove("span-mode-cursor");
        if (elements.spanGuideBanner) elements.spanGuideBanner.classList.add("hidden");
        clearSpanPreviewSvg();
        showStatus("Span well boundary placement cancelled.");
    }

    function clearSpanPreviewSvg() {
        if (!elements.gridOverlaySvg) return;
        const oldPreviews = elements.gridOverlaySvg.querySelectorAll(".span-preview-element");
        oldPreviews.forEach(el => el.remove());
    }

    function renderSpanPreview(pt1, pt2, labelsCount) {
        clearSpanPreviewSvg();
        if (!pt1 || !pt2 || !elements.gridOverlaySvg) return;
        
        const svgNS = "http://www.w3.org/2000/svg";
        
        // 1. Dashed interpolation reference line
        const line = document.createElementNS(svgNS, "line");
        line.setAttribute("x1", pt1.x);
        line.setAttribute("y1", pt1.y);
        line.setAttribute("x2", pt2.x);
        line.setAttribute("y2", pt2.y);
        line.setAttribute("stroke", "#FF0055");
        line.setAttribute("stroke-width", "2.5");
        line.setAttribute("stroke-dasharray", "6,4");
        line.classList.add("span-preview-element");
        elements.gridOverlaySvg.appendChild(line);
        
        // 2. Start point marker
        const c1 = document.createElementNS(svgNS, "circle");
        c1.setAttribute("cx", pt1.x);
        c1.setAttribute("cy", pt1.y);
        c1.setAttribute("r", "7");
        c1.setAttribute("fill", "rgba(255, 0, 85, 0.85)");
        c1.setAttribute("stroke", "#FFFFFF");
        c1.setAttribute("stroke-width", "2");
        c1.classList.add("span-preview-element");
        elements.gridOverlaySvg.appendChild(c1);
        
        // 3. End point marker
        const c2 = document.createElementNS(svgNS, "circle");
        c2.setAttribute("cx", pt2.x);
        c2.setAttribute("cy", pt2.y);
        c2.setAttribute("r", "7");
        c2.setAttribute("fill", "rgba(0, 255, 255, 0.85)");
        c2.setAttribute("stroke", "#FFFFFF");
        c2.setAttribute("stroke-width", "2");
        c2.classList.add("span-preview-element");
        elements.gridOverlaySvg.appendChild(c2);
        
        // 4. Intermediate tick markers showing lane positions
        if (labelsCount && labelsCount > 2) {
            for (let i = 1; i < labelsCount - 1; i++) {
                const t = i / (labelsCount - 1);
                const x = pt1.x + t * (pt2.x - pt1.x);
                const y = pt1.y + t * (pt2.y - pt1.y);
                const dot = document.createElementNS(svgNS, "circle");
                dot.setAttribute("cx", x);
                dot.setAttribute("cy", y);
                dot.setAttribute("r", "3.5");
                dot.setAttribute("fill", "#00FF00");
                dot.setAttribute("stroke", "#000000");
                dot.setAttribute("stroke-width", "1");
                dot.classList.add("span-preview-element");
                elements.gridOverlaySvg.appendChild(dot);
            }
        }
    }

    function createNewTabState(name) {
        return {
            id: generateId(),
            name: name || "Gel Tab",
            imageSrc: null,
            imageWidth: 0,
            imageHeight: 0,
            labels: {}, // Keyed by label.id
            selectedIds: [],
            gridEnabled: false,
            gridXSpacing: 40,
            gridYSpacing: 40,
            gridXOffset: 0,
            gridYOffset: 0,
            gridColor: "#E29C3D",
            slideTitle: "",
            defaultLabelFontFamily: "Arial",
            defaultLabelSize: 12,
            defaultLabelColor: "#00FF00",
            undoStack: [],
            redoStack: []
        };
    }

    function getActiveTab() {
        return state.tabs.find(t => t.id === state.activeTabId);
    }

    function saveUndoState(tab) {
        if (!tab) return;
        
        // Deep copy the labels list to restore later
        const serializedLabels = JSON.parse(JSON.stringify(tab.labels));
        tab.undoStack.push({
            labels: serializedLabels,
            selectedIds: [...tab.selectedIds]
        });
        tab.redoStack = []; // Clear redo stack on new operation
        updateHeaderActionButtons();
        autosaveSession();
    }

    function triggerUndo() {
        const tab = getActiveTab();
        if (!tab || tab.undoStack.length === 0) return;
        
        const currentLabels = JSON.parse(JSON.stringify(tab.labels));
        const currentSelected = [...tab.selectedIds];
        
        tab.redoStack.push({
            labels: currentLabels,
            selectedIds: currentSelected
        });
        
        const previousState = tab.undoStack.pop();
        tab.labels = previousState.labels;
        tab.selectedIds = previousState.selectedIds;
        
        renderActiveTabLabels();
        updateHeaderActionButtons();
        updateSelectionStatus();
        autosaveSession();
        showStatus("Undo completed.");
    }

    function triggerRedo() {
        const tab = getActiveTab();
        if (!tab || tab.redoStack.length === 0) return;
        
        const currentLabels = JSON.parse(JSON.stringify(tab.labels));
        const currentSelected = [...tab.selectedIds];
        
        tab.undoStack.push({
            labels: currentLabels,
            selectedIds: currentSelected
        });
        
        const nextState = tab.redoStack.pop();
        tab.labels = nextState.labels;
        tab.selectedIds = nextState.selectedIds;
        
        renderActiveTabLabels();
        updateHeaderActionButtons();
        updateSelectionStatus();
        autosaveSession();
        showStatus("Redo completed.");
    }

    function showStatus(msg) {
        elements.statusMessage.textContent = msg;
    }

    function updateSelectionStatus() {
        if (!elements.selectionCount) return;
        const tab = getActiveTab();
        const count = tab ? tab.selectedIds.length : 0;
        elements.selectionCount.innerHTML = `<i class="fa-solid fa-object-group"></i> ${count} selected`;
    }

    // --- Tab management UI ---

    function renderTabs() {
        elements.tabBar.innerHTML = "";
        state.tabs.forEach(tab => {
            const tabBtn = document.createElement("button");
            tabBtn.className = `gel-tab ${tab.id === state.activeTabId ? "active" : ""}`;
            
            // Icon
            const icon = document.createElement("i");
            icon.className = "fa-solid fa-file-invoice";
            
            // Title
            const titleSpan = document.createElement("span");
            titleSpan.textContent = tab.name;
            titleSpan.addEventListener("dblclick", (e) => {
                e.stopPropagation();
                renameTabInline(tab, titleSpan);
            });
            
            tabBtn.appendChild(icon);
            tabBtn.appendChild(titleSpan);
            
            // Close button
            if (state.tabs.length > 1) {
                const closeBtn = document.createElement("button");
                closeBtn.className = "tab-close-btn";
                closeBtn.innerHTML = "&times;";
                closeBtn.title = "Close Tab";
                closeBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    closeTab(tab.id);
                });
                tabBtn.appendChild(closeBtn);
            }
            
            tabBtn.addEventListener("click", () => {
                switchTab(tab.id);
            });
            
            elements.tabBar.appendChild(tabBtn);
        });
    }

    function renameTabInline(tab, spanNode) {
        const currentName = tab.name;
        const input = document.createElement("input");
        input.type = "text";
        input.value = currentName;
        input.className = "tab-rename-input";
        input.style.width = Math.max(60, currentName.length * 8) + "px";
        
        spanNode.replaceWith(input);
        input.focus();
        input.select();
        
        function commitRename() {
            const newName = input.value.trim();
            if (newName && newName !== currentName) {
                tab.name = newName;
                showStatus(`Renamed tab to "${newName}"`);
            }
            renderTabs();
            autosaveSession();
        }
        
        input.addEventListener("blur", commitRename);
        input.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                commitRename();
            } else if (e.key === "Escape") {
                input.replaceWith(spanNode);
                renderTabs();
            }
        });
    }

    function switchTab(tabId) {
        state.activeTabId = tabId;
        renderTabs();
        
        const tab = getActiveTab();
        if (!tab) return;
        
        // Sync UI settings panel controls with this tab's state
        syncSettingsPanelToTab(tab);
        
        // Show/hide canvas vs upload dropzone
        if (tab.imageSrc) {
            elements.uploadDropzone.classList.add("hidden");
            elements.canvasContainer.classList.remove("hidden");
            elements.gelImageDisplay.src = tab.imageSrc;
            if (elements.gelImgInfo) {
                elements.gelImgInfo.textContent = `${tab.name} (${tab.imageWidth}×${tab.imageHeight} px)`;
            }
            
            // Wait for image dimensions to confirm sizes
            elements.gelImageDisplay.onload = function() {
                elements.canvasWrapper.style.width = elements.gelImageDisplay.naturalWidth + "px";
                elements.canvasWrapper.style.height = elements.gelImageDisplay.naturalHeight + "px";
                elements.gridOverlaySvg.setAttribute("viewBox", `0 0 ${elements.gelImageDisplay.naturalWidth} ${elements.gelImageDisplay.naturalHeight}`);
                
                // Draw layers
                renderActiveTabGrid();
                renderActiveTabLabels();
            };
        } else {
            elements.uploadDropzone.classList.remove("hidden");
            elements.canvasContainer.classList.add("hidden");
            elements.gelImageDisplay.src = "";
            if (elements.gelImgInfo) {
                elements.gelImgInfo.textContent = "No image loaded (drop or browse)";
            }
        }
        
        applyCanvasZoom(1.0);
        updateHeaderActionButtons();
        updateSelectionStatus();
        showStatus(`Active gel tab: "${tab.name}"`);
    }

    function closeTab(tabId) {
        const index = state.tabs.findIndex(t => t.id === tabId);
        if (index === -1) return;
        
        state.tabs.splice(index, 1);
        
        // If active tab was deleted, switch to another tab
        if (state.activeTabId === tabId) {
            const nextActiveIndex = Math.max(0, index - 1);
            state.activeTabId = state.tabs[nextActiveIndex].id;
        }
        
        switchTab(state.activeTabId);
        autosaveSession();
    }

    function syncSettingsPanelToTab(tab) {
        // Font settings
        elements.fontFamilySelect.value = tab.defaultLabelFontFamily;
        elements.fontSizeInput.value = tab.defaultLabelSize;
        
        // Set active swatch color
        const swatches = elements.colorSwatches.querySelectorAll(".swatch");
        swatches.forEach(swatch => {
            if (swatch.dataset.color.toUpperCase() === tab.defaultLabelColor.toUpperCase()) {
                swatch.classList.add("active");
            } else {
                swatch.classList.remove("active");
            }
        });
        
        // Slide title
        elements.slideTitleInput.value = tab.slideTitle || "";
        
        // Reference grid checkbox and overlay values
        elements.gridEnableCheck.checked = tab.gridEnabled;
        if (tab.gridEnabled) {
            elements.gridControlsContainer.classList.add("visible");
        } else {
            elements.gridControlsContainer.classList.remove("visible");
        }
        
        elements.gridColorSelect.value = tab.gridColor;
        elements.gridXSpacing.value = tab.gridXSpacing;
        elements.gridXSpacingVal.textContent = tab.gridXSpacing;
        elements.gridYSpacing.value = tab.gridYSpacing;
        elements.gridYSpacingVal.textContent = tab.gridYSpacing;
        elements.gridXOffset.value = tab.gridXOffset;
        elements.gridXOffsetVal.textContent = tab.gridXOffset;
        elements.gridYOffset.value = tab.gridYOffset;
        elements.gridYOffsetVal.textContent = tab.gridYOffset;
    }

    function updateHeaderActionButtons() {
        const tab = getActiveTab();
        if (!tab) return;
        
        elements.undoBtn.disabled = tab.undoStack.length === 0;
        elements.redoBtn.disabled = tab.redoStack.length === 0;
        
        // Disable exports if no image is loaded
        const noImage = !tab.imageSrc;
        elements.exportImgBtn.disabled = noImage;
        elements.exportPptxBtn.disabled = noImage;
    }

    // --- Real-time Visual Reference Grid Drawing ---

    function renderActiveTabGrid() {
        const tab = getActiveTab();
        while (elements.gridOverlaySvg.firstChild) {
            elements.gridOverlaySvg.removeChild(elements.gridOverlaySvg.firstChild);
        }
        if (!tab || !tab.gridEnabled || !tab.imageWidth || !tab.imageHeight) {
            return;
        }
        
        const w = tab.imageWidth;
        const h = tab.imageHeight;
        
        const xSpacing = Math.max(5, tab.gridXSpacing);
        const ySpacing = Math.max(5, tab.gridYSpacing);
        const gridColor = sanitizeHexColor(tab.gridColor, "#E29C3D");
        
        const svgNS = "http://www.w3.org/2000/svg";
        const fragment = document.createDocumentFragment();
        
        // Vertical lines
        let xStart = (tab.gridXOffset % xSpacing);
        if (xStart > 0) {
            xStart -= xSpacing;
        }
        
        for (let x = xStart; x <= w; x += xSpacing) {
            if (x >= 0) {
                const line = document.createElementNS(svgNS, "line");
                line.setAttribute("x1", String(x));
                line.setAttribute("y1", "0");
                line.setAttribute("x2", String(x));
                line.setAttribute("y2", String(h));
                line.setAttribute("stroke", gridColor);
                line.setAttribute("stroke-width", "1");
                fragment.appendChild(line);
            }
        }
        
        // Horizontal lines
        let yStart = (tab.gridYOffset % ySpacing);
        if (yStart > 0) {
            yStart -= ySpacing;
        }
        
        for (let y = yStart; y <= h; y += ySpacing) {
            if (y >= 0) {
                const line = document.createElementNS(svgNS, "line");
                line.setAttribute("x1", "0");
                line.setAttribute("y1", String(y));
                line.setAttribute("x2", String(w));
                line.setAttribute("y2", String(y));
                line.setAttribute("stroke", gridColor);
                line.setAttribute("stroke-width", "1");
                fragment.appendChild(line);
            }
        }
        
        elements.gridOverlaySvg.appendChild(fragment);
    }

    // --- Interactive Labels Rendering and DOM Actions ---

    function renderActiveTabLabels() {
        const tab = getActiveTab();
        if (!tab) return;
        
        elements.labelsLayer.innerHTML = "";
        
        Object.values(tab.labels).forEach(label => {
            const lblNode = document.createElement("div");
            lblNode.className = `gel-label-item ${tab.selectedIds.includes(label.id) ? "selected" : ""}`;
            lblNode.id = `label-${label.id}`;
            lblNode.textContent = label.text;
            
            // Stylings
            lblNode.style.left = label.x + "px";
            lblNode.style.top = label.y + "px";
            lblNode.style.color = label.color;
            lblNode.style.fontFamily = label.fontFamily;
            lblNode.style.fontSize = label.fontSize + "px";
            lblNode.style.transform = `rotate(${label.rotation || 0}deg)`;
            
            // Event Listeners for Dragging & Selection
            lblNode.addEventListener("mousedown", (e) => {
                e.stopPropagation();
                handleLabelMouseDown(e, label);
            });
            
            lblNode.addEventListener("dblclick", (e) => {
                e.stopPropagation();
                openEditLabelModal(label);
            });
            
            elements.labelsLayer.appendChild(lblNode);
        });
    }

    function createNewLabel(tab, text, x, y) {
        saveUndoState(tab);
        
        const label = {
            id: generateId(),
            text: text,
            x: x,
            y: y,
            color: tab.defaultLabelColor,
            fontFamily: tab.defaultLabelFontFamily,
            fontSize: tab.defaultLabelSize,
            rotation: text.toLowerCase().includes("ladder") ? 270 : 0
        };
        
        tab.labels[label.id] = label;
        
        // Auto select newly placed label
        tab.selectedIds = [label.id];
        
        renderActiveTabLabels();
        updateSelectionStatus();
        autosaveSession();
        showStatus(`Placed label "${text}" at (${Math.round(x)}, ${Math.round(y)})`);
    }

    function incrementLabelString(str) {
        if (!str) return "1";
        const trimmed = str.trim();
        if (["ladder", "nc", "pc", "blank", "ctrl", "control", "water", "ntc", "marker"].includes(trimmed.toLowerCase())) {
            return str;
        }
        const match = str.match(/(\d+)$/);
        if (match) {
            const numStr = match[1];
            const nextNum = parseInt(numStr, 10) + 1;
            const paddedNextNum = nextNum.toString().padStart(numStr.length, "0");
            return str.slice(0, match.index) + paddedNextNum;
        }
        return str + "1";
    }

    // --- Interactive Mouse Handlers on Labels & Selection Box ---

    function handleLabelMouseDown(e, label) {
        const tab = getActiveTab();
        if (!tab) return;
        
        if (e.shiftKey) {
            // Toggle selection
            const idx = tab.selectedIds.indexOf(label.id);
            if (idx === -1) {
                tab.selectedIds.push(label.id);
            } else {
                tab.selectedIds.splice(idx, 1);
            }
        } else {
            // Standard single selection
            if (!tab.selectedIds.includes(label.id)) {
                tab.selectedIds = [label.id];
            }
        }
        
        renderActiveTabLabels();
        updateSelectionStatus();
        
        // Start dragging
        dragData.active = true;
        dragData.hasMoved = false;
        dragData.startX = e.clientX;
        dragData.startY = e.clientY;
        dragData.initialPositions = tab.selectedIds.map(id => {
            const l = tab.labels[id];
            return { id: l.id, x: l.x, y: l.y };
        });
        
        document.addEventListener("mousemove", handleLabelMouseMove);
        document.addEventListener("mouseup", handleLabelMouseUp);
    }

    function handleLabelMouseMove(e) {
        if (!dragData.active) return;
        
        const tab = getActiveTab();
        if (!tab) return;
        
        const dx = e.clientX - dragData.startX;
        const dy = e.clientY - dragData.startY;
        
        if (!dragData.hasMoved && (Math.abs(dx) > 1 || Math.abs(dy) > 1)) {
            saveUndoState(tab); // Save state on first actual movement
            dragData.hasMoved = true;
        }
        
        if (!dragData.hasMoved) return;
        
        // Update positions on screen in real-time
        dragData.initialPositions.forEach(pos => {
            const label = tab.labels[pos.id];
            if (label) {
                const domNode = document.getElementById(`label-${label.id}`);
                const lblW = domNode ? domNode.offsetWidth : 30;
                const lblH = domNode ? domNode.offsetHeight : 16;
                const maxW = tab.imageWidth > 0 ? Math.max(0, tab.imageWidth - lblW) : 10000;
                const maxH = tab.imageHeight > 0 ? Math.max(0, tab.imageHeight - lblH) : 10000;
                
                // Clamp within full element bounds
                label.x = Math.max(0, Math.min(maxW, pos.x + dx));
                label.y = Math.max(0, Math.min(maxH, pos.y + dy));
                
                if (domNode) {
                    domNode.style.left = label.x + "px";
                    domNode.style.top = label.y + "px";
                }
            }
        });
    }


    function handleLabelMouseUp() {
        if (dragData.active) {
            const hadMoved = dragData.hasMoved;
            dragData.active = false;
            dragData.hasMoved = false;
            document.removeEventListener("mousemove", handleLabelMouseMove);
            document.removeEventListener("mouseup", handleLabelMouseUp);
            if (hadMoved) {
                autosaveSession();
                showStatus("Moved selected labels.");
            }
        }
    }

    // --- Interactive Canvas Mouse Clicks & Rubber-Band Dragging ---

    elements.canvasViewport.addEventListener("mousedown", (e) => {
        const tab = getActiveTab();
        if (!tab || !tab.imageSrc) return;
        
        // 1. Handle Mark Well Boundaries (Span Mode)
        if (spanState.active) {
            if (e.button === 0) { // Left-click
                const rect = elements.canvasWrapper.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const clickY = e.clientY - rect.top;
                
                // Ensure click is within image bounds
                if (clickX >= 0 && clickX <= tab.imageWidth && clickY >= 0 && clickY <= tab.imageHeight) {
                    if (!spanState.firstPoint) {
                        // Capture First Point (leftmost well)
                        spanState.firstPoint = { x: Math.round(clickX), y: Math.round(clickY) };
                        if (elements.spanGuideBanner) {
                            elements.spanGuideText.innerHTML = `Span Mode: Click the <strong>rightmost well</strong> (2nd boundary point) for ${spanState.tierName}`;
                        }
                        renderSpanPreview(spanState.firstPoint, spanState.firstPoint, 0);
                        showStatus(`First well anchored at (${Math.round(clickX)}, ${Math.round(clickY)}). Now click the rightmost well.`);
                    } else {
                        // Capture Second Point (rightmost well) and generate labels
                        const pt1 = spanState.firstPoint;
                        const pt2 = { x: Math.round(clickX), y: Math.round(clickY) };
                        
                        const labels = parseLabelPattern(spanState.pattern);
                        if (labels.length === 0) {
                            showStatus("Error: No labels parsed from pattern.");
                            cancelSpanMode();
                            return;
                        }
                        
                        saveUndoState(tab);
                        
                        // Clear existing labels in span corridor to prevent overlap
                        const dx = pt2.x - pt1.x;
                        const dy = pt2.y - pt1.y;
                        const segLenSq = dx * dx + dy * dy;
                        
                        function distToSegment(px, py) {
                            if (segLenSq === 0) return Math.hypot(px - pt1.x, py - pt1.y);
                            const t = Math.max(0, Math.min(1, ((px - pt1.x) * dx + (py - pt1.y) * dy) / segLenSq));
                            const projX = pt1.x + t * dx;
                            const projY = pt1.y + t * dy;
                            return Math.hypot(px - projX, py - projY);
                        }
                        
                        Object.keys(tab.labels).forEach(lid => {
                            const lbl = tab.labels[lid];
                            if (distToSegment(lbl.x, lbl.y) <= 30) {
                                delete tab.labels[lid];
                            }
                        });
                        
                        // Linearly interpolate lane label positions
                        const nLabels = labels.length;
                        const placedIds = [];
                        for (let i = 0; i < nLabels; i++) {
                            const t = nLabels > 1 ? i / (nLabels - 1) : 0.5;
                            const x = pt1.x + t * (pt2.x - pt1.x);
                            const y = pt1.y + t * (pt2.y - pt1.y);
                            const labelText = labels[i];
                            
                            let rot = spanState.rotation;
                            // Automatic forced 270 deg rotation for any "Ladder" label if orientation is horizontal
                            if (labelText.toLowerCase().includes("ladder") && rot === 0) {
                                rot = 270;
                            }
                            
                            const newLbl = {
                                id: generateId(),
                                text: labelText,
                                x: Math.round(x),
                                y: Math.round(y),
                                color: tab.defaultLabelColor || "#00FF00",
                                fontFamily: tab.defaultLabelFontFamily || "Arial",
                                fontSize: spanState.fontSize || 12,
                                rotation: rot
                            };
                            tab.labels[newLbl.id] = newLbl;
                            placedIds.push(newLbl.id);
                        }
                        
                        tab.selectedIds = placedIds;
                        
                        cancelSpanMode();
                        renderActiveTabLabels();
                        updateSelectionStatus();
                        autosaveSession();
                        showStatus(`Successfully generated ${labels.length} well labels along boundary for ${spanState.tierName}!`);
                    }
                }
            } else if (e.button === 2) { // Right-click cancels span mode
                cancelSpanMode();
            }
            e.preventDefault();
            return;
        }
        
        // 2. Standard Interaction (Rubber-band marquee drag selection)
        const clickedOnLabel = e.target.closest(".gel-label-item");
        const clickedOnCanvas = e.target.closest("#canvas-wrapper");
        
        if (!clickedOnLabel && clickedOnCanvas) {
            // Clear selections unless shift is held
            if (!e.shiftKey) {
                tab.selectedIds = [];
                renderActiveTabLabels();
                updateSelectionStatus();
            }
            
            // Start selection box marquee
            selectionBox.active = true;
            selectionBox.startX = e.clientX - elements.canvasViewport.getBoundingClientRect().left;
            selectionBox.startY = e.clientY - elements.canvasViewport.getBoundingClientRect().top;
            
            selectionBox.domNode = document.createElement("div");
            selectionBox.domNode.className = "drag-selection-box";
            selectionBox.domNode.style.left = selectionBox.startX + "px";
            selectionBox.domNode.style.top = selectionBox.startY + "px";
            elements.canvasViewport.appendChild(selectionBox.domNode);
            
            document.addEventListener("mousemove", handleSelectionBoxMouseMove);
            document.addEventListener("mouseup", handleSelectionBoxMouseUp);
        }
    });

    // Dynamic Span Preview on Mouse Move
    if (elements.canvasWrapper) {
        elements.canvasWrapper.addEventListener("mousemove", (e) => {
            if (spanState.active && spanState.firstPoint) {
                const rect = elements.canvasWrapper.getBoundingClientRect();
                const curX = e.clientX - rect.left;
                const curY = e.clientY - rect.top;
                const labels = parseLabelPattern(spanState.pattern);
                renderSpanPreview(spanState.firstPoint, { x: curX, y: curY }, labels.length);
            }
        });
        
        // Double-click on empty canvas to create a label
        elements.canvasWrapper.addEventListener("dblclick", (e) => {
            if (spanState.active) return;
            const clickedOnLabel = e.target.closest(".gel-label-item");
            if (!clickedOnLabel) {
                const tab = getActiveTab();
                if (!tab || !tab.imageSrc) return;
                const rect = elements.canvasWrapper.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const clickY = e.clientY - rect.top;
                createNewLabel(tab, "Label", clickX, clickY);
            }
        });
        
        // Context menu on canvas wrapper cancels span mode if active
        elements.canvasWrapper.addEventListener("contextmenu", (e) => {
            if (spanState.active) {
                e.preventDefault();
                cancelSpanMode();
            }
        });
    }

    function handleSelectionBoxMouseMove(e) {
        if (!selectionBox.active) return;
        
        const viewportRect = elements.canvasViewport.getBoundingClientRect();
        const currentX = Math.max(0, Math.min(viewportRect.width, e.clientX - viewportRect.left));
        const currentY = Math.max(0, Math.min(viewportRect.height, e.clientY - viewportRect.top));
        
        const x = Math.min(selectionBox.startX, currentX);
        const y = Math.min(selectionBox.startY, currentY);
        const w = Math.abs(selectionBox.startX - currentX);
        const h = Math.abs(selectionBox.startY - currentY);
        
        selectionBox.domNode.style.left = x + "px";
        selectionBox.domNode.style.top = y + "px";
        selectionBox.domNode.style.width = w + "px";
        selectionBox.domNode.style.height = h + "px";
    }

    function handleSelectionBoxMouseUp(e) {
        if (!selectionBox.active) return;
        selectionBox.active = false;
        
        document.removeEventListener("mousemove", handleSelectionBoxMouseMove);
        document.removeEventListener("mouseup", handleSelectionBoxMouseUp);
        
        const tab = getActiveTab();
        if (!tab) return;
        
        // Find which labels are inside the selection box bounding rect
        const boxRect = selectionBox.domNode.getBoundingClientRect();
        
        Object.values(tab.labels).forEach(label => {
            const domNode = document.getElementById(`label-${label.id}`);
            if (domNode) {
                const labelRect = domNode.getBoundingClientRect();
                
                // Intersection test
                const intersect = !(
                    labelRect.left > boxRect.right ||
                    labelRect.right < boxRect.left ||
                    labelRect.top > boxRect.bottom ||
                    labelRect.bottom < boxRect.top
                );
                
                if (intersect) {
                    if (!tab.selectedIds.includes(label.id)) {
                        tab.selectedIds.push(label.id);
                    }
                }
            }
        });
        
        // Remove selection box DOM element
        if (selectionBox.domNode) {
            selectionBox.domNode.remove();
            selectionBox.domNode = null;
        }
        
        renderActiveTabLabels();
        updateSelectionStatus();
    }

    // --- Keyboard Arrow Nudging and Hotkeys ---

    window.addEventListener("keydown", (e) => {
        const isCtrl = e.ctrlKey || e.metaKey;
        const key = e.key;

        // Ignore hotkeys when typing in text fields / inputs, except Escape
        const isInputFocused = document.activeElement && (
            document.activeElement.tagName === "INPUT" ||
            document.activeElement.tagName === "SELECT" ||
            document.activeElement.tagName === "TEXTAREA"
        );

        if (key === "Escape") {
            if (spanState.active) {
                cancelSpanMode();
                e.preventDefault();
                return;
            }
            if (!isInputFocused) {
                const tab = getActiveTab();
                if (tab && tab.selectedIds.length > 0) {
                    tab.selectedIds = [];
                    renderActiveTabLabels();
                    updateSelectionStatus();
                    showStatus("Deselected all labels.");
                    e.preventDefault();
                    return;
                }
            }
        }

        if (isInputFocused) return;

        // Global hotkeys (Ctrl+A, Ctrl+Shift+A, Ctrl+Z, Ctrl+Y, Ctrl+B)
        if (isCtrl && key.toLowerCase() === "a") {
            if (e.shiftKey) {
                alignEverything();
            } else {
                selectAllLabels();
            }
            e.preventDefault();
            return;
        }

        if (isCtrl && key.toLowerCase() === "b") {
            enterSpanMode();
            e.preventDefault();
            return;
        }

        if (isCtrl && key.toLowerCase() === "z") {
            if (e.shiftKey) {
                triggerRedo();
            } else {
                triggerUndo();
            }
            e.preventDefault();
            return;
        }

        if (isCtrl && key.toLowerCase() === "y") {
            triggerRedo();
            e.preventDefault();
            return;
        }

        const tab = getActiveTab();
        if (!tab || tab.selectedIds.length === 0) return;
        
        // 1. Delete label
        if (key === "Delete" || key === "Backspace") {
            saveUndoState(tab);
            tab.selectedIds.forEach(id => {
                delete tab.labels[id];
            });
            tab.selectedIds = [];
            renderActiveTabLabels();
            updateSelectionStatus();
            autosaveSession();
            showStatus("Deleted selected labels.");
            e.preventDefault();
            return;
        }
        
        // 2. Selection cycle navigation via Enter
        if (key === "Enter") {
            const allLabels = Object.values(tab.labels);
            if (allLabels.length > 1) {
                // Sort primarily by Y (rounded to rows of 50px) and secondarily X
                const sorted = allLabels.sort((a,b) => {
                    const rowA = Math.round(a.y / 50) * 50;
                    const rowB = Math.round(b.y / 50) * 50;
                    if (rowA !== rowB) return rowA - rowB;
                    return a.x - b.x;
                });
                
                const currentId = tab.selectedIds[0];
                const currentIndex = sorted.findIndex(l => l.id === currentId);
                const nextIndex = (currentIndex + 1) % sorted.length;
                
                tab.selectedIds = [sorted[nextIndex].id];
                renderActiveTabLabels();
                updateSelectionStatus();
            }
            e.preventDefault();
            return;
        }
        
        // 3. Arrow nudge movement
        let dx = 0;
        let dy = 0;
        const step = e.shiftKey ? 5 : 1;
        
        if (key === "ArrowLeft") {
            dx = -step;
        } else if (key === "ArrowRight") {
            dx = step;
        } else if (key === "ArrowUp") {
            dy = -step;
        } else if (key === "ArrowDown") {
            dy = step;
        } else {
            return;
        }
        
        saveUndoState(tab);
        
        tab.selectedIds.forEach(id => {
            const label = tab.labels[id];
            if (label) {
                label.x = Math.max(0, Math.min(tab.imageWidth - 10, label.x + dx));
                label.y = Math.max(0, Math.min(tab.imageHeight - 10, label.y + dy));
            }
        });
        
        renderActiveTabLabels();
        autosaveSession();
        e.preventDefault();
    });

    // --- PPTX PowerPoint-Style Alignment and Distribution ---

    function alignLabels(type) {
        const tab = getActiveTab();
        if (!tab || tab.selectedIds.length < 2) {
            showStatus("Please select at least 2 labels to align.");
            return;
        }
        
        saveUndoState(tab);
        
        const selectedLabels = tab.selectedIds.map(id => tab.labels[id]).filter(Boolean);
        if (selectedLabels.length < 2) return;
        
        if (type === "Left") {
            const minX = Math.min(...selectedLabels.map(l => l.x));
            selectedLabels.forEach(l => l.x = minX);
            showStatus("Aligned selected labels Left.");
        } else if (type === "Center") {
            const avgX = Math.round(selectedLabels.reduce((s, l) => s + l.x, 0) / selectedLabels.length);
            selectedLabels.forEach(l => l.x = avgX);
            showStatus("Aligned selected labels Center.");
        } else if (type === "Right") {
            const maxX = Math.max(...selectedLabels.map(l => l.x));
            selectedLabels.forEach(l => l.x = maxX);
            showStatus("Aligned selected labels Right.");
        } else if (type === "Top") {
            const minY = Math.min(...selectedLabels.map(l => l.y));
            selectedLabels.forEach(l => l.y = minY);
            showStatus("Aligned selected labels Top.");
        } else if (type === "Middle") {
            const avgY = Math.round(selectedLabels.reduce((s, l) => s + l.y, 0) / selectedLabels.length);
            selectedLabels.forEach(l => l.y = avgY);
            showStatus("Aligned selected labels Middle.");
        } else if (type === "Bottom") {
            const maxY = Math.max(...selectedLabels.map(l => l.y));
            selectedLabels.forEach(l => l.y = maxY);
            showStatus("Aligned selected labels Bottom.");
        } else if (type === "DistributeHorizontally") {
            if (selectedLabels.length < 3) {
                showStatus("Select at least 3 labels to distribute horizontally.");
                return;
            }
            selectedLabels.sort((a, b) => a.x - b.x);
            const leftmostX = selectedLabels[0].x;
            const rightmostX = selectedLabels[selectedLabels.length - 1].x;
            const spacing = (rightmostX - leftmostX) / (selectedLabels.length - 1);
            
            for (let i = 1; i < selectedLabels.length - 1; i++) {
                selectedLabels[i].x = Math.round(leftmostX + i * spacing);
            }
            showStatus("Distributed selected labels horizontally.");
        } else if (type === "DistributeVertically") {
            if (selectedLabels.length < 3) {
                showStatus("Select at least 3 labels to distribute vertically.");
                return;
            }
            selectedLabels.sort((a, b) => a.y - b.y);
            const topmostY = selectedLabels[0].y;
            const bottommostY = selectedLabels[selectedLabels.length - 1].y;
            const spacing = (bottommostY - topmostY) / (selectedLabels.length - 1);
            
            for (let i = 1; i < selectedLabels.length - 1; i++) {
                selectedLabels[i].y = Math.round(topmostY + i * spacing);
            }
            showStatus("Distributed selected labels vertically.");
        }
        
        renderActiveTabLabels();
        autosaveSession();
    }

    function selectAllLabels() {
        const tab = getActiveTab();
        if (!tab || Object.keys(tab.labels).length === 0) {
            showStatus("No labels on canvas to select.");
            return;
        }
        tab.selectedIds = Object.keys(tab.labels);
        renderActiveTabLabels();
        updateSelectionStatus();
        showStatus(`Selected all ${tab.selectedIds.length} labels.`);
    }

    function alignEverything() {
        const tab = getActiveTab();
        if (!tab || Object.keys(tab.labels).length < 2) {
            showStatus("Need at least 2 labels to auto-align.");
            return;
        }
        saveUndoState(tab);
        
        // Group labels into horizontal rows (within 35px vertically)
        const allLabels = Object.values(tab.labels);
        const rows = [];
        allLabels.forEach(lbl => {
            let foundRow = rows.find(r => Math.abs(r.avgY - lbl.y) < 35);
            if (foundRow) {
                foundRow.labels.push(lbl);
                foundRow.avgY = foundRow.labels.reduce((s, l) => s + l.y, 0) / foundRow.labels.length;
            } else {
                rows.push({ avgY: lbl.y, labels: [lbl] });
            }
        });
        
        rows.forEach(r => {
            if (r.labels.length >= 2) {
                const targetY = Math.round(r.avgY);
                r.labels.sort((a, b) => a.x - b.x);
                const minX = r.labels[0].x;
                const maxX = r.labels[r.labels.length - 1].x;
                const spacing = (maxX - minX) / (r.labels.length - 1);
                r.labels.forEach((l, i) => {
                    l.y = targetY;
                    if (r.labels.length > 2 && i > 0 && i < r.labels.length - 1) {
                        l.x = Math.round(minX + i * spacing);
                    }
                });
            }
        });
        
        renderActiveTabLabels();
        autosaveSession();
        showStatus("Auto-aligned all horizontal tiers and vertical lanes!");
    }

    // --- Canvas Zoom & View Controls ---
    let canvasZoom = 1.0;

    function applyCanvasZoom(zoom) {
        canvasZoom = Math.max(0.2, Math.min(4.0, zoom));
        if (elements.canvasWrapper) {
            elements.canvasWrapper.style.transform = `scale(${canvasZoom})`;
            elements.canvasWrapper.style.transformOrigin = "center center";
        }
        if (elements.zoomResetBtn) {
            elements.zoomResetBtn.textContent = `${Math.round(canvasZoom * 100)}%`;
        }
    }

    function zoomIn() {
        applyCanvasZoom(canvasZoom * 1.2);
    }

    function zoomOut() {
        applyCanvasZoom(canvasZoom / 1.2);
    }

    function zoomReset() {
        applyCanvasZoom(1.0);
    }

    function zoomFit() {
        const tab = getActiveTab();
        if (!tab || !tab.imageWidth || !tab.imageHeight) {
            applyCanvasZoom(1.0);
            return;
        }
        const vpRect = elements.canvasViewport.getBoundingClientRect();
        const scaleX = (vpRect.width - 60) / tab.imageWidth;
        const scaleY = (vpRect.height - 60) / tab.imageHeight;
        const fitScale = Math.min(scaleX, scaleY, 1.0);
        applyCanvasZoom(Math.max(0.25, fitScale));
    }

    // --- Modeless Simulated Edit Properties Dialog ---

    let currentEditingLabel = null;

    function openEditLabelModal(label) {
        currentEditingLabel = label;
        elements.editLabelText.value = label.text;
        elements.editLabelFont.value = label.fontFamily;
        elements.editLabelSize.value = label.fontSize;
        elements.editLabelColor.value = label.color.startsWith("#") ? label.color : "#00FF00";
        elements.editLabelRotation.value = label.rotation || 0;
        
        elements.editLabelModal.classList.remove("hidden");
        elements.editLabelText.focus();
        elements.editLabelText.select();
    }

    function closeEditLabelModal() {
        elements.editLabelModal.classList.add("hidden");
        currentEditingLabel = null;
    }

    elements.editLabelSaveBtn.addEventListener("click", () => {
        if (!currentEditingLabel) return;
        const tab = getActiveTab();
        if (!tab) return;
        
        saveUndoState(tab);
        
        // Apply changes
        currentEditingLabel.text = elements.editLabelText.value.trim() || "Label";
        currentEditingLabel.fontFamily = elements.editLabelFont.value;
        currentEditingLabel.fontSize = parseInt(elements.editLabelSize.value, 10) || 12;
        currentEditingLabel.color = elements.editLabelColor.value;
        currentEditingLabel.rotation = parseInt(elements.editLabelRotation.value, 10) || 0;
        
        closeEditLabelModal();
        renderActiveTabLabels();
        autosaveSession();
        showStatus("Label properties updated.");
    });

    elements.editLabelDeleteBtn.addEventListener("click", () => {
        if (!currentEditingLabel) return;
        const tab = getActiveTab();
        if (!tab) return;
        
        saveUndoState(tab);
        
        delete tab.labels[currentEditingLabel.id];
        // Remove from selected list
        tab.selectedIds = tab.selectedIds.filter(id => id !== currentEditingLabel.id);
        
        closeEditLabelModal();
        renderActiveTabLabels();
        updateSelectionStatus();
        autosaveSession();
        showStatus("Label deleted.");
    });

    elements.editLabelCancelBtn.addEventListener("click", closeEditLabelModal);
    elements.modalCloseBtn.addEventListener("click", closeEditLabelModal);

    // --- Image File Upload Handlers ---

    function handleImageFileLoad(file) {
        if (!file || !file.type.match("image.*")) {
            showStatus("Error: Unsupported file format. Please upload an image file.");
            return;
        }
        
        const tab = getActiveTab();
        if (!tab) return;
        
        const reader = new FileReader();
        showStatus("Loading gel electrophoresis image...");
        
        reader.onload = function(event) {
            const dataUrl = event.target.result;
            
            // Create offscreen image to check native width & height
            const img = new Image();
            img.onload = function() {
                tab.imageSrc = dataUrl;
                tab.imageWidth = img.width;
                tab.imageHeight = img.height;
                tab.name = file.name;
                
                // Clear any old selection/redo
                tab.labels = {};
                tab.selectedIds = [];
                tab.undoStack = [];
                tab.redoStack = [];
                
                switchTab(tab.id); // Triggers canvas wrapper resize, grid, and labels load
                autosaveSession();
                showStatus(`Successfully loaded image: ${file.name} (${img.width}x${img.height} px)`);
            };
            img.src = dataUrl;
        };
        
        reader.readAsDataURL(file);
    }

    // Drag-and-Drop dropzone listeners
    elements.canvasViewport.addEventListener("dragover", (e) => {
        e.preventDefault();
        elements.uploadDropzone.classList.add("dragover");
    });

    elements.canvasViewport.addEventListener("dragleave", (e) => {
        elements.uploadDropzone.classList.remove("dragover");
    });

    elements.canvasViewport.addEventListener("drop", (e) => {
        e.preventDefault();
        elements.uploadDropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleImageFileLoad(e.dataTransfer.files[0]);
        }
    });

    elements.fileUploadInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleImageFileLoad(e.target.files[0]);
        }
    });

    // Track mouse coordinates on hover
    elements.canvasViewport.addEventListener("mousemove", (e) => {
        const clickedOnCanvas = e.target.closest("#canvas-wrapper");
        if (clickedOnCanvas) {
            const rect = elements.canvasWrapper.getBoundingClientRect();
            const x = Math.round(e.clientX - rect.left);
            const y = Math.round(e.clientY - rect.top);
            elements.coordDisplay.innerHTML = `<i class="fa-solid fa-crosshairs"></i> X: ${x} , Y: ${y}`;
        } else {
            elements.coordDisplay.innerHTML = `<i class="fa-solid fa-crosshairs"></i> X: - , Y: -`;
        }
    });

    // --- Local storage Autosave & Recovery System ---

    function autosaveSession() {
        // Prepare data without heavy undo stacks to save storage space
        const autosaveData = {
            activeTabId: state.activeTabId,
            tabs: state.tabs.map(t => ({
                id: t.id,
                name: t.name,
                imageSrc: t.imageSrc,
                imageWidth: t.imageWidth,
                imageHeight: t.imageHeight,
                labels: t.labels,
                selectedIds: t.selectedIds,
                gridEnabled: t.gridEnabled,
                gridXSpacing: t.gridXSpacing,
                gridYSpacing: t.gridYSpacing,
                gridXOffset: t.gridXOffset,
                gridYOffset: t.gridYOffset,
                gridColor: t.gridColor,
                slideTitle: t.slideTitle,
                defaultLabelFontFamily: t.defaultLabelFontFamily,
                defaultLabelSize: t.defaultLabelSize,
                defaultLabelColor: t.defaultLabelColor
            }))
        };
        
        try {
            localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(autosaveData));
        } catch(e) {
            console.warn("Autosave failed (likely storage quota exceeded for base64 images)", e);
        }
    }

    function recoverSession() {
        const stored = localStorage.getItem(LOCAL_STORAGE_KEY);
        if (!stored) return false;
        
        try {
            const parsed = JSON.parse(stored);
            if (!parsed || !Array.isArray(parsed.tabs) || parsed.tabs.length === 0) return false;
            
            // Re-inflate tabs with strict validation
            state.tabs = parsed.tabs.map(t => {
                if (!t || typeof t !== "object") return createNewTabState();
                
                const validLabels = {};
                if (t.labels && typeof t.labels === "object") {
                    Object.values(t.labels).forEach(lbl => {
                        if (lbl && typeof lbl === "object" && lbl.id) {
                            const lblId = String(lbl.id);
                            validLabels[lblId] = {
                                id: lblId,
                                text: sanitizeText(lbl.text || ""),
                                x: sanitizeNumber(lbl.x, 0, 0, 50000),
                                y: sanitizeNumber(lbl.y, 0, 0, 50000),
                                color: sanitizeHexColor(lbl.color, "#00FF00"),
                                fontFamily: typeof lbl.fontFamily === "string" ? lbl.fontFamily.slice(0, 50) : "Arial",
                                fontSize: Math.round(sanitizeNumber(lbl.fontSize, 12, 4, 144)),
                                rotation: sanitizeNumber(lbl.rotation, 0, -360, 360) % 360
                            };
                        }
                    });
                }
                
                const validSelectedIds = Array.isArray(t.selectedIds)
                    ? t.selectedIds.map(String).filter(id => Boolean(validLabels[id]))
                    : [];
                
                return {
                    id: typeof t.id === "string" ? t.id : generateId(),
                    name: sanitizeText(t.name || "Gel Tab"),
                    imageSrc: (typeof t.imageSrc === "string" && (t.imageSrc.startsWith("data:image/") || t.imageSrc.startsWith("blob:") || t.imageSrc.startsWith("http"))) ? t.imageSrc : null,
                    imageWidth: Math.round(sanitizeNumber(t.imageWidth, 0, 0, 50000)),
                    imageHeight: Math.round(sanitizeNumber(t.imageHeight, 0, 0, 50000)),
                    labels: validLabels,
                    selectedIds: validSelectedIds,
                    gridEnabled: Boolean(t.gridEnabled),
                    gridXSpacing: Math.round(sanitizeNumber(t.gridXSpacing, 40, 5, 500)),
                    gridYSpacing: Math.round(sanitizeNumber(t.gridYSpacing, 40, 5, 500)),
                    gridXOffset: Math.round(sanitizeNumber(t.gridXOffset, 0, -500, 500)),
                    gridYOffset: Math.round(sanitizeNumber(t.gridYOffset, 0, -500, 500)),
                    gridColor: sanitizeHexColor(t.gridColor, "#E29C3D"),
                    slideTitle: sanitizeText(t.slideTitle || ""),
                    defaultLabelFontFamily: typeof t.defaultLabelFontFamily === "string" ? t.defaultLabelFontFamily.slice(0, 50) : "Arial",
                    defaultLabelSize: Math.round(sanitizeNumber(t.defaultLabelSize, 12, 6, 72)),
                    defaultLabelColor: sanitizeHexColor(t.defaultLabelColor, "#00FF00"),
                    undoStack: [],
                    redoStack: []
                };
            });
            
            const validActive = state.tabs.find(t => t.id === parsed.activeTabId);
            state.activeTabId = validActive ? validActive.id : state.tabs[0].id;
            tabCounter = Math.max(state.tabs.length + 1, tabCounter);
            return true;

        } catch(e) {
            console.error("Failed to recover stored session", e);
            return false;
        }
    }

    // --- Export as Image (HTML5 Canvas Render) ---

    function exportAnnotatedImage() {
        const tab = getActiveTab();
        if (!tab || !tab.imageSrc) {
            showStatus("No image to export.");
            return;
        }
        
        showStatus("Rendering annotated image...");
        
        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement("canvas");
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext("2d");
            
            // 1. Draw Gel background
            ctx.drawImage(img, 0, 0);
            
            // 2. Draw labels
            Object.values(tab.labels).forEach(label => {
                ctx.save();
                
                // Bounding calculations
                const family = label.fontFamily || 'Arial';
                const fontSpec = family.includes(' ') && !family.startsWith('"') ? `"${family}"` : family;
                ctx.font = `bold ${label.fontSize}px ${fontSpec}`;
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";

                
                const textMetrics = ctx.measureText(label.text);
                const textWidth = textMetrics.width;
                const textHeight = label.fontSize;
                
                // Translate context to center of label box (matching DOM padding of 4px horizontal, 2px vertical)
                const cx = label.x + (textWidth + 8) / 2;
                const cy = label.y + (textHeight + 4) / 2;
                ctx.translate(cx, cy);
                
                // Apply rotation around center
                if (label.rotation) {
                    ctx.rotate((label.rotation * Math.PI) / 180);
                }
                
                // Draw high-contrast outline for legibility
                ctx.strokeStyle = "#000000";
                ctx.lineWidth = Math.max(2, Math.round(label.fontSize * 0.22));
                ctx.lineJoin = "round";
                ctx.miterLimit = 2;
                ctx.strokeText(label.text, 0, 0);
                
                // Draw text
                ctx.fillStyle = label.color;
                ctx.fillText(label.text, 0, 0);
                
                ctx.restore();
            });
            
            // 3. Trigger download
            const dataUrl = canvas.toDataURL("image/png");
            const link = document.createElement("a");
            link.download = tab.name.replace(/\.[^/.]+$/, "") + "_annotated.png";
            link.href = dataUrl;
            link.click();
            showStatus("PNG image exported successfully.");
        };
        img.src = tab.imageSrc;
    }

    // --- Export as PowerPoint Slide using PptxGenJS ---

    function exportToPowerPoint() {
        const tab = getActiveTab();
        if (!tab || !tab.imageSrc) {
            showStatus("No active gel image to export.");
            return;
        }
        
        showStatus("Compiling PowerPoint slides...");
        
        const pptx = new PptxGenJS();
        pptx.layout = 'LAYOUT_WIDE'; // standard widescreen 16:9 ratio
        
        // We will loop and add a slide for each tab that contains an image
        state.tabs.forEach(t => {
            if (!t.imageSrc) return;
            
            const slide = pptx.addSlide();
            const slideTitle = t.slideTitle.trim();
            const hasTitle = slideTitle.length > 0;
            
            // Add Title if specified
            if (hasTitle) {
                slide.addText(slideTitle, {
                    x: 0.5,
                    y: 0.4,
                    w: 12.33,
                    h: 0.8,
                    align: 'center',
                    fontFace: 'Arial',
                    fontSize: 24,
                    bold: true,
                    color: '282828'
                });
            }
            
            // Fit layout to center the gel image on the 13.33" x 7.5" widescreen slide
            const slideWIn = 13.33;
            const slideHIn = 7.5;
            
            const availHIn = hasTitle ? 5.7 : 7.5;
            const topOffsetIn = hasTitle ? 1.3 : 0.0;
            
            const scale = Math.min(slideWIn / t.imageWidth, availHIn / t.imageHeight);
            
            const imgWIn = t.imageWidth * scale;
            const imgHIn = t.imageHeight * scale;
            
            const leftIn = (slideWIn - imgWIn) / 2.0;
            const topIn = topOffsetIn + (availHIn - imgHIn) / 2.0;
            
            // 1. Add background picture
            slide.addImage({
                data: t.imageSrc, // base64 data url
                x: leftIn,
                y: topIn,
                w: imgWIn,
                h: imgHIn
            });
            
            // 2. Add text boxes for labels
            Object.values(t.labels).forEach(label => {
                // Approximate bounding boxes
                const wPx = Math.max(15.0, label.text.length * label.fontSize * 0.6 + 10.0);
                const hPx = label.fontSize * 1.5;
                
                // Center coordinates in pixels
                const cxPx = label.x + wPx / 2.0;
                const cyPx = label.y + hPx / 2.0;
                
                // Convert center to slide inches
                const cxIn = leftIn + cxPx * scale;
                const cyIn = topIn + cyPx * scale;
                
                const boxWIn = (wPx + 10.0) * scale;
                const boxHIn = (hPx + 2.0) * scale;
                
                const tx = cxIn - boxWIn / 2.0;
                const ty = cyIn - boxHIn / 2.0;
                
                // Convert px to pt for PowerPoint text
                const fontSizePt = Math.max(6, Math.round(label.fontSize * 0.75));
                const fontColorHex = label.color.replace("#", "");
                
                slide.addText(label.text, {
                    x: tx,
                    y: ty,
                    w: boxWIn,
                    h: boxHIn,
                    align: 'center',
                    valign: 'middle',
                    fontFace: label.fontFamily || 'Arial',
                    fontSize: fontSizePt,
                    bold: true,
                    color: fontColorHex,
                    rotate: label.rotation || 0,
                    margin: 0
                });
            });
        });
        
        // Trigger save
        const outputName = tab.name.replace(/\.[^/.]+$/, "") + "_slides.pptx";
        pptx.writeFile({ fileName: outputName })
            .then(() => {
                showStatus("PowerPoint widescreen deck exported successfully.");
            })
            .catch(e => {
                showStatus("Error exporting PPTX: " + e.message);
            });
    }

    // --- UI Controls Event Listeners ---

    // Mark Well Boundaries (Span Mode) Action Listeners
    if (elements.startSpanBtn) {
        elements.startSpanBtn.addEventListener("click", () => {
            enterSpanMode();
        });
    }

    if (elements.cancelSpanBtn) {
        elements.cancelSpanBtn.addEventListener("click", () => {
            cancelSpanMode();
        });
    }

    if (elements.spanTierSelect) {
        elements.spanTierSelect.addEventListener("change", (e) => {
            spanState.tierName = e.target.value;
            if (spanState.active && elements.spanGuideText) {
                const ptStep = spanState.firstPoint ? "rightmost well (2nd boundary point)" : "leftmost well (1st boundary point)";
                elements.spanGuideText.innerHTML = `Span Mode: Click the <strong>${ptStep}</strong> for ${spanState.tierName}`;
            }
        });
    }

    if (elements.spanPatternInput) {
        elements.spanPatternInput.addEventListener("input", (e) => {
            spanState.pattern = e.target.value;
        });
    }

    if (elements.spanRotationSelect) {
        elements.spanRotationSelect.addEventListener("change", (e) => {
            spanState.rotation = parseInt(e.target.value, 10) || 0;
        });
    }

    if (elements.spanSizeInput) {
        elements.spanSizeInput.addEventListener("input", (e) => {
            spanState.fontSize = parseInt(e.target.value, 10) || 12;
        });
    }

    // Font selection changes
    elements.fontFamilySelect.addEventListener("change", (e) => {
        const tab = getActiveTab();
        if (!tab) return;
        
        tab.defaultLabelFontFamily = e.target.value;
        
        // If labels are selected, apply batch font update!
        if (tab.selectedIds.length > 0) {
            saveUndoState(tab);
            tab.selectedIds.forEach(id => {
                const label = tab.labels[id];
                if (label) label.fontFamily = e.target.value;
            });
            renderActiveTabLabels();
        }
        autosaveSession();
    });

    elements.fontSizeInput.addEventListener("change", (e) => {
        const tab = getActiveTab();
        if (!tab) return;
        
        const newSize = parseInt(e.target.value, 10) || 12;
        tab.defaultLabelSize = newSize;
        
        // If labels are selected, apply batch size update!
        if (tab.selectedIds.length > 0) {
            saveUndoState(tab);
            tab.selectedIds.forEach(id => {
                const label = tab.labels[id];
                if (label) label.fontSize = newSize;
            });
            renderActiveTabLabels();
        }
        autosaveSession();
    });

    // Color Swatches
    elements.colorSwatches.addEventListener("click", (e) => {
        const swatch = e.target.closest(".swatch");
        if (!swatch) return;
        
        const tab = getActiveTab();
        if (!tab) return;
        
        const selectedColor = swatch.dataset.color;
        tab.defaultLabelColor = selectedColor;
        
        // Toggle UI highlights
        elements.colorSwatches.querySelectorAll(".swatch").forEach(s => s.classList.remove("active"));
        swatch.classList.add("active");
        
        // If labels are selected, apply batch color update!
        if (tab.selectedIds.length > 0) {
            saveUndoState(tab);
            tab.selectedIds.forEach(id => {
                const label = tab.labels[id];
                if (label) label.color = selectedColor;
            });
            renderActiveTabLabels();
        }
        autosaveSession();
    });

    // Alignments & Distribution
    if (elements.alignLeftBtn) elements.alignLeftBtn.addEventListener("click", () => alignLabels("Left"));
    if (elements.alignCenterBtn) elements.alignCenterBtn.addEventListener("click", () => alignLabels("Center"));
    if (elements.alignRightBtn) elements.alignRightBtn.addEventListener("click", () => alignLabels("Right"));
    if (elements.alignTopBtn) elements.alignTopBtn.addEventListener("click", () => alignLabels("Top"));
    if (elements.alignMiddleBtn) elements.alignMiddleBtn.addEventListener("click", () => alignLabels("Middle"));
    if (elements.alignBottomBtn) elements.alignBottomBtn.addEventListener("click", () => alignLabels("Bottom"));
    if (elements.distHorizBtn) elements.distHorizBtn.addEventListener("click", () => alignLabels("DistributeHorizontally"));
    if (elements.distVertBtn) elements.distVertBtn.addEventListener("click", () => alignLabels("DistributeVertically"));
    if (elements.selectAllBtn) elements.selectAllBtn.addEventListener("click", selectAllLabels);
    if (elements.headerSelectAllBtn) elements.headerSelectAllBtn.addEventListener("click", selectAllLabels);
    if (elements.floatingSelectAllBtn) elements.floatingSelectAllBtn.addEventListener("click", selectAllLabels);
    if (elements.alignEverythingBtn) elements.alignEverythingBtn.addEventListener("click", alignEverything);

    // Zoom & Canvas View Controls
    if (elements.zoomInBtn) elements.zoomInBtn.addEventListener("click", zoomIn);
    if (elements.zoomOutBtn) elements.zoomOutBtn.addEventListener("click", zoomOut);
    if (elements.zoomResetBtn) elements.zoomResetBtn.addEventListener("click", zoomReset);
    if (elements.zoomFitBtn) elements.zoomFitBtn.addEventListener("click", zoomFit);

    // Extra File Input Handlers (Header & Sidebar)
    if (elements.headerFileInput) {
        elements.headerFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) handleImageFileLoad(e.target.files[0]);
        });
    }
    if (elements.sidebarFileInput) {
        elements.sidebarFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) handleImageFileLoad(e.target.files[0]);
        });
    }
    if (elements.colonyHeaderFileInput) {
        elements.colonyHeaderFileInput.addEventListener("change", (e) => {
            if (e.target.files.length > 0) handleColonyImageFile(e.target.files[0]);
        });
    }

    // Grid checkbox and sliders
    elements.gridEnableCheck.addEventListener("change", (e) => {
        const tab = getActiveTab();
        if (!tab) return;
        
        tab.gridEnabled = e.target.checked;
        if (tab.gridEnabled) {
            elements.gridControlsContainer.classList.add("visible");
        } else {
            elements.gridControlsContainer.classList.remove("visible");
        }
        renderActiveTabGrid();
        autosaveSession();
    });

    elements.gridColorSelect.addEventListener("change", (e) => {
        const tab = getActiveTab();
        if (tab) {
            tab.gridColor = e.target.value;
            renderActiveTabGrid();
            autosaveSession();
        }
    });

    function handleGridSliderInput(sliderNode, valueSpanNode, stateKey) {
        sliderNode.addEventListener("input", (e) => {
            const tab = getActiveTab();
            if (tab) {
                const val = parseInt(e.target.value, 10);
                valueSpanNode.textContent = val;
                tab[stateKey] = val;
                renderActiveTabGrid();
            }
        });
        
        sliderNode.addEventListener("change", () => {
            autosaveSession();
        });
    }

    handleGridSliderInput(elements.gridXSpacing, elements.gridXSpacingVal, "gridXSpacing");
    handleGridSliderInput(elements.gridYSpacing, elements.gridYSpacingVal, "gridYSpacing");
    handleGridSliderInput(elements.gridXOffset, elements.gridXOffsetVal, "gridXOffset");
    handleGridSliderInput(elements.gridYOffset, elements.gridYOffsetVal, "gridYOffset");

    // Slide Customizations
    elements.slideTitleInput.addEventListener("input", (e) => {
        const tab = getActiveTab();
        if (tab) {
            tab.slideTitle = e.target.value;
            autosaveSession();
        }
    });

    elements.clearLabelsBtn.addEventListener("click", () => {
        const tab = getActiveTab();
        if (!tab || Object.keys(tab.labels).length === 0) return;
        
        if (confirm("Are you sure you want to delete all labels on the current tab?")) {
            saveUndoState(tab);
            tab.labels = {};
            tab.selectedIds = [];
            renderActiveTabLabels();
            updateSelectionStatus();
            autosaveSession();
            showStatus("All labels cleared.");
        }
    });

    // Undo / Redo Click actions
    elements.undoBtn.addEventListener("click", triggerUndo);
    elements.redoBtn.addEventListener("click", triggerRedo);

    // Export Buttons
    elements.exportImgBtn.addEventListener("click", exportAnnotatedImage);
    elements.exportPptxBtn.addEventListener("click", exportToPowerPoint);

    // Tab Adding
    elements.addTabBtn.addEventListener("click", () => {
        const newTab = createNewTabState(`Gel ${tabCounter++}`);
        state.tabs.push(newTab);
        switchTab(newTab.id);
        autosaveSession();
    });


    // Click on canvas viewport to deselect all labels
    elements.canvasViewport.addEventListener("click", (e) => {
        const clickedOnLabel = e.target.closest(".gel-label-item");
        const clickedOnControls = e.target.closest(".control-panel");
        const clickedOnHeader = e.target.closest(".app-header");
        const clickedOnModal = e.target.closest(".modal-card");
        
        if (!clickedOnLabel && !clickedOnControls && !clickedOnHeader && !clickedOnModal) {
            const tab = getActiveTab();
            if (tab && tab.selectedIds.length > 0) {
                tab.selectedIds = [];
                renderActiveTabLabels();
                updateSelectionStatus();
            }
        }
    });

    // =========================================================================
    // ================== GEL LABELER MODULE NAVIGATION =====================
    // =========================================================================

    let currentModule = "gel"; // "gel" or "colony"

    function switchSuiteModule(moduleName) {
        currentModule = moduleName;
        if (moduleName === "gel") {
            elements.navGelBtn.classList.add("active");
            elements.navColonyBtn.classList.remove("active");
            elements.gelModule.classList.remove("hidden");
            elements.colonyModule.classList.add("hidden");
            elements.gelTabBarContainer.classList.remove("hidden");
            elements.gelGlobalActions.classList.remove("hidden");
            elements.colonyGlobalActions.classList.add("hidden");
            showStatus("Active module: PCR Gel Genie");
        } else if (moduleName === "colony") {
            elements.navColonyBtn.classList.add("active");
            elements.navGelBtn.classList.remove("active");
            elements.colonyModule.classList.remove("hidden");
            elements.gelModule.classList.add("hidden");
            elements.gelTabBarContainer.classList.add("hidden");
            elements.gelGlobalActions.classList.add("hidden");
            elements.colonyGlobalActions.classList.remove("hidden");
            showStatus("Active module: Colony & Seed AI Counter");
        }
    }

    elements.navGelBtn.addEventListener("click", () => switchSuiteModule("gel"));
    elements.navColonyBtn.addEventListener("click", () => switchSuiteModule("colony"));

    // =========================================================================
    // ================== COLONY & SEED AI VISION COUNTER ======================
    // =========================================================================

    let colonyState = {
        imageSrc: null,
        imageWidth: 0,
        imageHeight: 0,
        fileName: "",
        colonies: [],
        dishCircle: null,
        rawCanvas: null
    };

    function handleColonyImageFile(file) {
        if (!file || !file.type.match("image.*")) {
            showStatus("Error: Please select a valid image file.");
            return;
        }

        const reader = new FileReader();
        showStatus("Loading plate image...");

        reader.onload = function(e) {
            const dataUrl = e.target.result;
            const img = new Image();
            img.onload = function() {
                colonyState.imageSrc = dataUrl;
                colonyState.imageWidth = img.width;
                colonyState.imageHeight = img.height;
                colonyState.fileName = file.name;
                colonyState.colonies = [];

                // Create offscreen analysis canvas
                const offCanvas = document.createElement("canvas");
                offCanvas.width = img.width;
                offCanvas.height = img.height;
                const ctx = offCanvas.getContext("2d");
                ctx.drawImage(img, 0, 0);
                colonyState.rawCanvas = offCanvas;

                // Update UI Display
                elements.colonyDropzone.classList.add("hidden");
                elements.colonyCanvasContainer.classList.remove("hidden");
                elements.colonyImageDisplay.src = dataUrl;
                elements.colonyCanvasWrapper.style.width = img.width + "px";
                elements.colonyCanvasWrapper.style.height = img.height + "px";
                elements.colonyDishSvg.setAttribute("viewBox", `0 0 ${img.width} ${img.height}`);
                elements.colonyImgInfo.textContent = `${file.name} (${img.width}x${img.height} px)`;

                runColonyAiDetection();
                showStatus(`Plate loaded: ${file.name}`);
            };
            img.src = dataUrl;
        };
        reader.readAsDataURL(file);
    }

    // Computer vision detection algorithm
    function runColonyAiDetection() {
        if (!colonyState.rawCanvas) return;

        const w = colonyState.imageWidth;
        const h = colonyState.imageHeight;
        const ctx = colonyState.rawCanvas.getContext("2d");
        const imgData = ctx.getImageData(0, 0, w, h);
        const data = imgData.data;

        const sens = parseInt(elements.colonySensSlider.value, 10);
        const minRad = parseInt(elements.colonyMinRad.value, 10);
        const maxRad = parseInt(elements.colonyMaxRad.value, 10);
        const circMin = parseInt(elements.colonyCircSlider.value, 10) / 100.0;
        const maskDish = elements.colonyMaskDish.checked;
        const invert = elements.colonyInvertMode.checked;

        // 1. Petri dish circular boundary
        const cx = Math.floor(w / 2);
        const cy = Math.floor(h / 2);
        const dishR = Math.floor(Math.min(w, h) * 0.46);
        colonyState.dishCircle = maskDish ? { cx, cy, r: dishR } : null;

        // Render dish boundary SVG
        if (colonyState.dishCircle) {
            elements.colonyDishSvg.innerHTML = `<circle cx="${cx}" cy="${cy}" r="${dishR}" stroke="#00FFCC" stroke-width="2" stroke-dasharray="6,4" fill="none" />`;
        } else {
            elements.colonyDishSvg.innerHTML = "";
        }

        // 2. Grayscale & Adaptive Local Thresholding
        const gray = new Uint8Array(w * h);
        let sum = 0;
        for (let i = 0, j = 0; i < data.length; i += 4, j++) {
            const g = Math.round(data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114);
            gray[j] = g;
            sum += g;
        }
        const meanIntensity = sum / (w * h);

        // Compute local variance and threshold
        const binary = new Uint8Array(w * h);
        const thresholdOffset = (50 - sens) * 0.4;
        const baseThreshold = meanIntensity + (invert ? thresholdOffset : -thresholdOffset);

        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const idx = y * w + x;
                // Check if inside dish circle mask
                if (maskDish) {
                    const distFromCenter = Math.hypot(x - cx, y - cy);
                    if (distFromCenter > dishR * 0.96) {
                        binary[idx] = 0;
                        continue;
                    }
                }
                const g = gray[idx];
                const isForeground = invert ? (g > baseThreshold) : (g < baseThreshold);
                binary[idx] = isForeground ? 1 : 0;
            }
        }

        // 3. Connected Component Flood-Fill & Centroid Extraction
        const visited = new Uint8Array(w * h);
        const detectedColonies = [];
        let nextId = 1;

        const minArea = Math.PI * (minRad * minRad) * 0.5;
        const maxArea = Math.PI * (maxRad * maxRad) * 1.6;

        // Grid-based sampling for high-speed scanning
        const step = Math.max(1, Math.floor(minRad * 0.5));

        for (let y = 0; y < h; y += step) {
            for (let x = 0; x < w; x += step) {
                const idx = y * w + x;
                if (binary[idx] === 1 && visited[idx] === 0) {
                    // BFS Flood fill component
                    const queue = [[x, y]];
                    visited[idx] = 1;

                    let area = 0;
                    let sumX = 0;
                    let sumY = 0;
                    let minX = x, maxX = x, minY = y, maxY = y;
                    let perimeter = 0;

                    let qHead = 0;
                    while (qHead < queue.length) {
                        const [currX, currY] = queue[qHead++];
                        area++;
                        sumX += currX;
                        sumY += currY;

                        if (currX < minX) minX = currX;
                        if (currX > maxX) maxX = currX;
                        if (currY < minY) minY = currY;
                        if (currY > maxY) maxY = currY;

                        // Check 4-neighbors
                        let isEdge = false;
                        const neighbors = [
                            [currX + 1, currY],
                            [currX - 1, currY],
                            [currX, currY + 1],
                            [currX, currY - 1]
                        ];

                        for (let n = 0; n < 4; n++) {
                            const [nx, ny] = neighbors[n];
                            if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                                const nIdx = ny * w + nx;
                                if (binary[nIdx] === 1) {
                                    if (visited[nIdx] === 0) {
                                        visited[nIdx] = 1;
                                        queue.push([nx, ny]);
                                    }
                                } else {
                                    isEdge = true;
                                }
                            } else {
                                isEdge = true;
                            }
                        }
                        if (isEdge) perimeter++;
                    }

                    if (area >= minArea && area <= maxArea) {
                        // Circularity calculation: 4 * PI * Area / (Perimeter^2)
                        const circularity = perimeter > 0 ? (4 * Math.PI * area) / (perimeter * perimeter) : 0;
                        if (circularity >= circMin) {
                            const objCenterX = sumX / area;
                            const objCenterY = sumY / area;
                            const estRadius = Math.max(minRad, Math.min(maxRad, Math.sqrt(area / Math.PI)));

                            detectedColonies.push({
                                id: nextId++,
                                x: Math.round(objCenterX),
                                y: Math.round(objCenterY),
                                radius: Math.round(estRadius),
                                area: Math.round(area),
                                isManual: false
                            });
                        }
                    }
                }
            }
        }

        // Separate and preserve manual markers
        const manualMarkers = (colonyState.colonies || []).filter(c => c.isManual);
        let finalColonies = detectedColonies;
        let nextManualId = detectedColonies.length + 1;
        manualMarkers.forEach(m => {
            m.id = nextManualId++;
            finalColonies.push(m);
        });

        colonyState.colonies = finalColonies;
        renderColonyMarkers();
        updateColonyStatistics();
    }

    let colonyDetectTimer = null;
    function debouncedColonyAiDetection(delayMs = 120) {
        if (colonyDetectTimer) clearTimeout(colonyDetectTimer);
        colonyDetectTimer = setTimeout(() => {
            runColonyAiDetection();
        }, delayMs);
    }

    function renderColonyMarkers() {
        elements.colonyMarkersLayer.innerHTML = "";

        const color = elements.colonyColorSelect.value;
        const size = parseInt(elements.colonyMarkerSize.value, 10);
        const showNums = elements.colonyShowNumbers.checked;

        colonyState.colonies.forEach(col => {
            const markerNode = document.createElement("div");
            markerNode.className = "colony-marker-node";
            markerNode.style.left = col.x + "px";
            markerNode.style.top = col.y + "px";
            markerNode.style.width = (size * 2) + "px";
            markerNode.style.height = (size * 2) + "px";
            markerNode.style.border = `2px solid ${color}`;
            markerNode.style.backgroundColor = `${color}44`;

            if (showNums) {
                const idSpan = document.createElement("span");
                idSpan.className = "colony-marker-id";
                idSpan.textContent = col.id;
                markerNode.appendChild(idSpan);
            }

            // Click to delete on individual marker
            markerNode.addEventListener("click", (e) => {
                e.stopPropagation();
                deleteColonyMarker(col.id);
            });

            markerNode.addEventListener("contextmenu", (e) => {
                e.preventDefault();
                e.stopPropagation();
                deleteColonyMarker(col.id);
            });

            elements.colonyMarkersLayer.appendChild(markerNode);
        });
    }

    function addManualColonyMarker(clickX, clickY) {
        const nextId = (colonyState.colonies.reduce((max, c) => Math.max(max, c.id), 0) || 0) + 1;
        const size = parseInt(elements.colonyMarkerSize.value, 10);

        colonyState.colonies.push({
            id: nextId,
            x: Math.round(clickX),
            y: Math.round(clickY),
            radius: size,
            area: Math.round(Math.PI * size * size),
            isManual: true
        });

        renderColonyMarkers();
        updateColonyStatistics();
        showStatus(`Added manual colony #${nextId} at (${Math.round(clickX)}, ${Math.round(clickY)})`);
    }

    function deleteColonyMarker(colonyId) {
        const idx = colonyState.colonies.findIndex(c => c.id === colonyId);
        if (idx !== -1) {
            colonyState.colonies.splice(idx, 1);
            renderColonyMarkers();
            updateColonyStatistics();
            showStatus(`Removed colony marker #${colonyId}`);
        }
    }

    function updateColonyStatistics() {
        const count = colonyState.colonies.length;
        const vol = parseFloat(elements.colonyVolumeInput.value) || 0.1;
        const dilution = parseFloat(elements.colonyDilutionSelect.value) || 1.0;

        const cfu = vol > 0 ? (count * dilution) / vol : 0;

        elements.colonyStatCount.textContent = `${count} colonies`;
        elements.colonyStatCfu.textContent = cfu.toLocaleString("en-US", { maximumFractionDigits: 1 });
    }

    // Colony Viewport Click Handler (Manual Click-to-add)
    elements.colonyViewport.addEventListener("click", (e) => {
        if (!colonyState.imageSrc) return;
        const clickedOnMarker = e.target.closest(".colony-marker-node");
        const clickedOnCanvas = e.target.closest("#colony-canvas-wrapper");

        if (!clickedOnMarker && clickedOnCanvas) {
            const rect = elements.colonyCanvasWrapper.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;
            addManualColonyMarker(clickX, clickY);
        }
    });

    // Colony Parameter Inputs Live Tuning with Debounce
    elements.colonySensSlider.addEventListener("input", (e) => {
        elements.colonySensVal.textContent = e.target.value;
        debouncedColonyAiDetection(120);
    });

    elements.colonyCircSlider.addEventListener("input", (e) => {
        elements.colonyCircVal.textContent = (parseInt(e.target.value, 10) / 100).toFixed(2);
        debouncedColonyAiDetection(120);
    });

    elements.colonyMinRad.addEventListener("change", () => debouncedColonyAiDetection(50));
    elements.colonyMaxRad.addEventListener("change", () => debouncedColonyAiDetection(50));
    elements.colonyMaskDish.addEventListener("change", () => debouncedColonyAiDetection(50));
    elements.colonyInvertMode.addEventListener("change", () => debouncedColonyAiDetection(50));

    // Marker styling changes

    elements.colonyColorSelect.addEventListener("change", renderColonyMarkers);
    elements.colonyMarkerSize.addEventListener("change", renderColonyMarkers);
    elements.colonyShowNumbers.addEventListener("change", renderColonyMarkers);

    // CFU inputs
    elements.colonyVolumeInput.addEventListener("input", updateColonyStatistics);
    elements.colonyDilutionSelect.addEventListener("change", updateColonyStatistics);

    // File Drop & Browse Listeners for Colony Counter
    elements.colonyFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) handleColonyImageFile(e.target.files[0]);
    });
    elements.colonyFileInputBtn.addEventListener("change", (e) => {
        if (e.target.files.length > 0) handleColonyImageFile(e.target.files[0]);
    });

    elements.colonyViewport.addEventListener("dragover", (e) => {
        e.preventDefault();
        elements.colonyDropzone.classList.add("dragover");
    });
    elements.colonyViewport.addEventListener("dragleave", () => {
        elements.colonyDropzone.classList.remove("dragover");
    });
    elements.colonyViewport.addEventListener("drop", (e) => {
        e.preventDefault();
        elements.colonyDropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleColonyImageFile(e.dataTransfer.files[0]);
        }
    });

    // Colony Exports (PNG & CSV)
    function exportColonyAnnotatedImage() {
        if (!colonyState.imageSrc || colonyState.colonies.length === 0) {
            showStatus("No colony data to export.");
            return;
        }

        const img = new Image();
        img.onload = function() {
            const canvas = document.createElement("canvas");
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext("2d");

            // 1. Draw plate photo
            ctx.drawImage(img, 0, 0);

            // 2. Draw dish circle if active
            if (colonyState.dishCircle) {
                ctx.strokeStyle = "#00FFCC";
                ctx.lineWidth = 3;
                ctx.setLineDash([8, 6]);
                ctx.beginPath();
                ctx.arc(colonyState.dishCircle.cx, colonyState.dishCircle.cy, colonyState.dishCircle.r, 0, 2 * Math.PI);
                ctx.stroke();
                ctx.setLineDash([]);
            }

            // 3. Draw markers
            const color = elements.colonyColorSelect.value;
            const size = parseInt(elements.colonyMarkerSize.value, 10);
            const showNums = elements.colonyShowNumbers.checked;

            ctx.font = `bold ${Math.max(10, size)}px Arial`;
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";

            colonyState.colonies.forEach(col => {
                ctx.strokeStyle = color;
                ctx.lineWidth = 2.5;
                ctx.beginPath();
                ctx.arc(col.x, col.y, size, 0, 2 * Math.PI);
                ctx.stroke();

                ctx.fillStyle = `${color}55`;
                ctx.fill();

                if (showNums) {
                    ctx.fillStyle = "#FFFFFF";
                    ctx.strokeStyle = "#000000";
                    ctx.lineWidth = 2;
                    ctx.strokeText(col.id.toString(), col.x + size + 2, col.y);
                    ctx.fillText(col.id.toString(), col.x + size + 2, col.y);
                }
            });

            // 4. Download file
            const dataUrl = canvas.toDataURL("image/png");
            const link = document.createElement("a");
            link.download = (colonyState.fileName || "plate").replace(/\.[^/.]+$/, "") + "_counted.png";
            link.href = dataUrl;
            link.click();
            showStatus("Annotated plate image exported successfully.");
        };
        img.src = colonyState.imageSrc;
    }

    function exportColonyCsvTable() {
        if (colonyState.colonies.length === 0) {
            showStatus("No colonies detected to export.");
            return;
        }

        const vol = parseFloat(elements.colonyVolumeInput.value) || 0.1;
        const dilution = parseFloat(elements.colonyDilutionSelect.value) || 1.0;
        const cfu = vol > 0 ? (colonyState.colonies.length * dilution) / vol : 0;

        const lines = [
            "# Gel Labeler - Colony & Seed AI Vision Report",
            `Source Image,${sanitizeCsvCellJs(colonyState.fileName || "Unknown")}`,
            `Total Count,${colonyState.colonies.length}`,
            `Plated Volume (mL),${vol}`,
            `Dilution Factor,${dilution}`,
            `Calculated CFU/mL,${cfu.toFixed(2)}`,
            "",
            "Colony ID,X (px),Y (px),Radius (px),Area (px^2),Type"
        ];

        colonyState.colonies.forEach(c => {
            lines.push([
                sanitizeCsvCellJs(c.id),
                c.x,
                c.y,
                c.radius,
                c.area,
                sanitizeCsvCellJs(c.isManual ? "Manual" : "AI Detected")
            ].join(","));
        });

        const csvContent = lines.join("\r\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        const cleanBase = (colonyState.fileName || "plate").replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_\-]/g, "_");
        link.setAttribute("download", `${cleanBase}_colony_report.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        showStatus("Colony CSV report exported successfully.");
    }

    elements.colonyExportImgBtn.addEventListener("click", exportColonyAnnotatedImage);
    elements.colonyExportCsvBtn.addEventListener("click", exportColonyCsvTable);

    // --- Application Bootstrapping ---

    function initializeApplication() {
        const recovered = recoverSession();
        
        if (!recovered) {
            // Setup default workspace (tab 1)
            const initialTab = createNewTabState("Gel 1");
            state.tabs.push(initialTab);
            state.activeTabId = initialTab.id;
        }
        
        switchTab(state.activeTabId);
        showStatus("Gel Labeler initialized. Ready for operations.");
    }

    initializeApplication();

})();
