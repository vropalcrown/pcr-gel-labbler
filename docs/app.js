// PCR Gel Genie - Web Gel Labeler Core Application Script

(function() {
    // --- Application State ---
    let state = {
        tabs: [],
        activeTabId: null,
        clipboard: []
    };

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
        undoBtn: document.getElementById("undo-btn"),
        redoBtn: document.getElementById("redo-btn"),
        exportImgBtn: document.getElementById("export-img-btn"),
        exportPptxBtn: document.getElementById("export-pptx-btn"),
        clickModeSelect: document.getElementById("click-mode-select"),
        customTextInputWrap: document.getElementById("custom-text-input-wrap"),
        customTextInput: document.getElementById("custom-text-input"),
        fontFamilySelect: document.getElementById("font-family-select"),
        fontSizeInput: document.getElementById("font-size-input"),
        colorSwatches: document.getElementById("color-swatches"),
        alignLeftBtn: document.getElementById("align-left-btn"),
        alignTopBtn: document.getElementById("align-top-btn"),
        distHorizBtn: document.getElementById("dist-horiz-btn"),
        distVertBtn: document.getElementById("dist-vert-btn"),
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
        canvasContainer: document.getElementById("canvas-container"),
        canvasWrapper: document.getElementById("canvas-wrapper"),
        gelImageDisplay: document.getElementById("gel-image-display"),
        gridOverlaySvg: document.getElementById("grid-overlay-svg"),
        labelsLayer: document.getElementById("labels-layer"),
        canvasViewport: document.getElementById("canvas-viewport"),
        statusMessage: document.getElementById("status-message"),
        coordDisplay: document.getElementById("coord-display"),
        // Suite Navigation
        navGelBtn: document.getElementById("nav-gel-btn"),
        navColonyBtn: document.getElementById("nav-colony-btn"),
        gelModule: document.getElementById("gel-module"),
        colonyModule: document.getElementById("colony-module"),
        gelTabBarContainer: document.getElementById("gel-tab-bar-container"),
        gelGlobalActions: document.getElementById("gel-global-actions"),
        colonyGlobalActions: document.getElementById("colony-global-actions"),
        
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
            clickMode: "disabled",
            nextLabelText: "L1",
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
        const tab = getActiveTab();
        if (!tab) {
            elements.selectionCount.innerHTML = `<i class="fa-solid fa-object-group"></i> 0 selected`;
            return;
        }
        elements.selectionCount.innerHTML = `<i class="fa-solid fa-object-group"></i> ${tab.selectedIds.length} selected`;
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
        }
        
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
        // Mode dropdown
        elements.clickModeSelect.value = tab.clickMode;
        if (tab.clickMode === "custom" || tab.clickMode === "auto-number") {
            elements.customTextInputWrap.classList.add("visible");
            elements.customTextInput.value = tab.nextLabelText;
        } else {
            elements.customTextInputWrap.classList.remove("visible");
        }
        
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
        if (!tab || !tab.gridEnabled || !tab.imageWidth || !tab.imageHeight) {
            elements.gridOverlaySvg.innerHTML = "";
            return;
        }
        
        const w = tab.imageWidth;
        const h = tab.imageHeight;
        
        const xSpacing = Math.max(5, tab.gridXSpacing);
        const ySpacing = Math.max(5, tab.gridYSpacing);
        
        let svgContent = "";
        
        // Vertical lines
        let xStart = (tab.gridXOffset % xSpacing);
        if (xStart > 0) {
            xStart -= xSpacing;
        }
        
        for (let x = xStart; x <= w; x += xSpacing) {
            if (x >= 0) {
                svgContent += `<line x1="${x}" y1="0" x2="${x}" y2="${h}" stroke="${tab.gridColor}" stroke-width="1" />`;
            }
        }
        
        // Horizontal lines
        let yStart = (tab.gridYOffset % ySpacing);
        if (yStart > 0) {
            yStart -= ySpacing;
        }
        
        for (let y = yStart; y <= h; y += ySpacing) {
            if (y >= 0) {
                svgContent += `<line x1="0" y1="${y}" x2="${w}" y2="${y}" stroke="${tab.gridColor}" stroke-width="1" />`;
            }
        }
        
        elements.gridOverlaySvg.innerHTML = svgContent;
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
        
        // Handle auto-incrementing text
        if (tab.clickMode === "auto-number" || tab.clickMode === "custom") {
            tab.nextLabelText = incrementLabelString(tab.nextLabelText);
            elements.customTextInput.value = tab.nextLabelText;
        }
        
        renderActiveTabLabels();
        updateSelectionStatus();
        autosaveSession();
        showStatus(`Placed label "${text}" at (${Math.round(x)}, ${Math.round(y)})`);
    }

    function incrementLabelString(str) {
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
                // Clamp within bounds
                label.x = Math.max(0, Math.min(tab.imageWidth - 10, pos.x + dx));
                label.y = Math.max(0, Math.min(tab.imageHeight - 10, pos.y + dy));
                
                const domNode = document.getElementById(`label-${label.id}`);
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
        
        // Clicking outside active label clears selections unless shift is pressed or placement mode is active
        const clickedOnLabel = e.target.closest(".gel-label-item");
        const clickedOnCanvas = e.target.closest("#canvas-wrapper");
        
        if (!clickedOnLabel && clickedOnCanvas) {
            const rect = elements.canvasWrapper.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const clickY = e.clientY - rect.top;
            
            if (tab.clickMode !== "disabled") {
                // Placement mode active -> Add label
                const labelText = (tab.clickMode === "auto-number" || tab.clickMode === "custom") ? tab.nextLabelText : "Label";
                createNewLabel(tab, labelText, clickX, clickY);
            } else {
                // Disabled mode -> Initiate rubber-band drag marquee selection
                if (!e.shiftKey) {
                    tab.selectedIds = [];
                    renderActiveTabLabels();
                    updateSelectionStatus();
                }
                
                // Start selection box selection
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
        }
    });

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
        const tab = getActiveTab();
        if (!tab || tab.selectedIds.length === 0) return;
        
        // Disable nudging/deletes if user is typing in inputs or forms
        if (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "SELECT") {
            return;
        }
        
        const key = e.key;
        
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
            // Check for Ctrl+Z undo hotkeys
            if (e.ctrlKey && key.toLowerCase() === "z") {
                triggerUndo();
                e.preventDefault();
            } else if (e.ctrlKey && key.toLowerCase() === "y") {
                triggerRedo();
                e.preventDefault();
            }
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
        
        if (type === "Left") {
            const minX = Math.min(...selectedLabels.map(l => l.x));
            selectedLabels.forEach(l => l.x = minX);
            showStatus("Aligned selected labels Left.");
        } else if (type === "Top") {
            const minY = Math.min(...selectedLabels.map(l => l.y));
            selectedLabels.forEach(l => l.y = minY);
            showStatus("Aligned selected labels Top.");
        } else if (type === "DistributeHorizontally") {
            if (selectedLabels.length < 3) {
                showStatus("Select at least 3 labels to distribute.");
                return;
            }
            // Sort left-to-right
            selectedLabels.sort((a, b) => a.x - b.x);
            const leftmostX = selectedLabels[0].x;
            const rightmostX = selectedLabels[selectedLabels.length - 1].x;
            const spacing = (rightmostX - leftmostX) / (selectedLabels.length - 1);
            
            for (let i = 1; i < selectedLabels.length - 1; i++) {
                selectedLabels[i].x = leftmostX + i * spacing;
            }
            showStatus("Distributed selected labels horizontally.");
        } else if (type === "DistributeVertically") {
            if (selectedLabels.length < 3) {
                showStatus("Select at least 3 labels to distribute.");
                return;
            }
            // Sort top-to-bottom
            selectedLabels.sort((a, b) => a.y - b.y);
            const topmostY = selectedLabels[0].y;
            const bottommostY = selectedLabels[selectedLabels.length - 1].y;
            const spacing = (bottommostY - topmostY) / (selectedLabels.length - 1);
            
            for (let i = 1; i < selectedLabels.length - 1; i++) {
                selectedLabels[i].y = topmostY + i * spacing;
            }
            showStatus("Distributed selected labels vertically.");
        }
        
        renderActiveTabLabels();
        autosaveSession();
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
        
        // Special constraint matching: force Ladder rotation if rename contains ladder
        if (currentEditingLabel.text.toLowerCase().includes("ladder")) {
            currentEditingLabel.rotation = 270;
        }
        
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
                clickMode: t.clickMode,
                nextLabelText: t.nextLabelText,
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
            if (!parsed.tabs || parsed.tabs.length === 0) return false;
            
            // Re-inflate tabs including empty stacks
            state.tabs = parsed.tabs.map(t => ({
                ...t,
                undoStack: [],
                redoStack: []
            }));
            state.activeTabId = parsed.activeTabId || state.tabs[0].id;
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
                ctx.font = `bold ${label.fontSize}px ${label.fontFamily || 'Arial'}`;
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

    // Placed Click Mode Select
    elements.clickModeSelect.addEventListener("change", (e) => {
        const tab = getActiveTab();
        if (!tab) return;
        
        tab.clickMode = e.target.value;
        if (tab.clickMode === "custom" || tab.clickMode === "auto-number") {
            elements.customTextInputWrap.classList.add("visible");
            tab.nextLabelText = elements.customTextInput.value;
        } else {
            elements.customTextInputWrap.classList.remove("visible");
        }
        autosaveSession();
    });

    elements.customTextInput.addEventListener("input", (e) => {
        const tab = getActiveTab();
        if (tab) {
            tab.nextLabelText = e.target.value;
            autosaveSession();
        }
    });

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

    // Alignments
    elements.alignLeftBtn.addEventListener("click", () => alignLabels("Left"));
    elements.alignTopBtn.addEventListener("click", () => alignLabels("Top"));
    elements.distHorizBtn.addEventListener("click", () => alignLabels("DistributeHorizontally"));
    elements.distVertBtn.addEventListener("click", () => alignLabels("DistributeVertically"));

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
        const newCount = state.tabs.length + 1;
        const newTab = createNewTabState(`Gel ${newCount}`);
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

        colonyState.colonies = detectedColonies;
        renderColonyMarkers();
        updateColonyStatistics();
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

    // Colony Parameter Inputs Live Tuning
    elements.colonySensSlider.addEventListener("input", (e) => {
        elements.colonySensVal.textContent = e.target.value;
        runColonyAiDetection();
    });

    elements.colonyCircSlider.addEventListener("input", (e) => {
        elements.colonyCircVal.textContent = (parseInt(e.target.value, 10) / 100).toFixed(2);
        runColonyAiDetection();
    });

    elements.colonyMinRad.addEventListener("change", runColonyAiDetection);
    elements.colonyMaxRad.addEventListener("change", runColonyAiDetection);
    elements.colonyMaskDish.addEventListener("change", runColonyAiDetection);
    elements.colonyInvertMode.addEventListener("change", runColonyAiDetection);

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
        const cfu = (colonyState.colonies.length * dilution) / vol;

        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "# Gel Labeler - Colony & Seed AI Vision Report\n";
        csvContent += `Source Image,${colonyState.fileName || "Unknown"}\n`;
        csvContent += `Total Count,${colonyState.colonies.length}\n`;
        csvContent += `Plated Volume (mL),${vol}\n`;
        csvContent += `Dilution Factor,${dilution}\n`;
        csvContent += `Calculated CFU/mL,${cfu.toFixed(2)}\n\n`;
        csvContent += "Colony ID,X (px),Y (px),Radius (px),Area (px^2),Type\n";

        colonyState.colonies.forEach(c => {
            csvContent += `${c.id},${c.x},${c.y},${c.radius},${c.area},${c.isManual ? "Manual" : "AI Detected"}\n`;
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", (colonyState.fileName || "plate").replace(/\.[^/.]+$/, "") + "_colony_report.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
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
