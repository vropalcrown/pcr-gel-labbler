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
        selectionCount: document.getElementById("selection-count"),
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
        modalCloseBtn: document.getElementById("modal-close-btn")
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
        dragData.startX = e.clientX;
        dragData.startY = e.clientY;
        dragData.initialPositions = tab.selectedIds.map(id => {
            const l = tab.labels[id];
            return { id: l.id, x: l.x, y: l.y };
        });
        
        saveUndoState(tab); // Save state before moving starts
        
        document.addEventListener("mousemove", handleLabelMouseMove);
        document.addEventListener("mouseup", handleLabelMouseUp);
    }

    function handleLabelMouseMove(e) {
        if (!dragData.active) return;
        
        const tab = getActiveTab();
        if (!tab) return;
        
        const dx = e.clientX - dragData.startX;
        const dy = e.clientY - dragData.startY;
        
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
            dragData.active = false;
            document.removeEventListener("mousemove", handleLabelMouseMove);
            document.removeEventListener("mouseup", handleLabelMouseUp);
            autosaveSession();
            showStatus("Moved selected labels.");
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
                const textWidth = ctx.measureText(label.text).width;
                const textHeight = label.fontSize; // Approximation
                
                // Translate context to center of label
                const cx = label.x + textWidth / 2;
                const cy = label.y + textHeight / 2;
                ctx.translate(cx, cy);
                
                // Apply rotation
                if (label.rotation) {
                    ctx.rotate((label.rotation * Math.PI) / 180);
                }
                
                // Draw outline for legibility
                ctx.strokeStyle = "#000000";
                ctx.lineWidth = 3;
                ctx.lineJoin = "round";
                ctx.miterLimit = 2;
                ctx.strokeText(label.text, -textWidth / 2, textHeight / 2);
                
                // Draw text
                ctx.fillStyle = label.color;
                ctx.fillText(label.text, -textWidth / 2, textHeight / 2);
                
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
        showStatus("Web Gel Labeler initialized. Ready for operations.");
    }

    initializeApplication();

})();
