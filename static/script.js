document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    const input = document.getElementById('component-query');
    const chips = document.querySelectorAll('.chip');
    const terminal = document.getElementById('terminal-output');
    const researchSection = document.getElementById('research-progress');
    const resultsDisplay = document.getElementById('results-display');

    // Handle Search
    const performSearch = async (query) => {
        if (!query) return;

        // Reset UI
        terminal.innerHTML = '';
        researchSection.classList.remove('hidden');
        resultsDisplay.classList.add('hidden');
        resultsDisplay.classList.add('hidden');
        
        // Connect to SSE
        const eventSource = new EventSource(`/api/stream?q=${encodeURIComponent(query)}`);

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'trace') {
                addTerminalStep(data.data);
            } else if (data.type === 'complete') {
                eventSource.close();
                fetchFinalReport(query);
            } else if (data.type === 'error') {
                eventSource.close();
                addTerminalStep(`Error: ${data.data}`, 'error');
            }
        };

        eventSource.onerror = (err) => {
            console.error('SSE Error:', err);
            eventSource.close();
        };
    };

    const addTerminalStep = (text, type = 'info') => {
        const step = document.createElement('div');
        step.className = 'terminal-step';
        
        const icon = document.createElement('span');
        icon.innerHTML = '>>';
        icon.style.color = type === 'error' ? 'var(--error)' : 'var(--primary)';
        
        const content = document.createElement('span');
        content.textContent = text;
        if (type === 'error') content.style.color = 'var(--error)';

        step.appendChild(icon);
        step.appendChild(content);
        terminal.appendChild(step);
        terminal.scrollTop = terminal.scrollHeight;
    };

    const fetchFinalReport = async (query) => {
        try {
            const response = await fetch(`/api/report?q=${encodeURIComponent(query)}`);
            const report = await response.json();
            renderResults(report);
        } catch (err) {
            console.error('Fetch error:', err);
        }
    };

    const renderResults = (report) => {
        resultsDisplay.classList.remove('hidden');
        resultsDisplay.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        // 1. Render Header Box
        const headerContainer = document.getElementById('box-header');
        headerContainer.innerHTML = `
            <div class="component-title">
                <div>
                    <h2 style="font-size: 2.5rem; margin-bottom: 0.5rem;">${report.component_name || 'N/A'}</h2>
                    <span class="badge" style="font-size: 1rem; padding: 0.5rem 1rem;">${report.manufacturer || 'Unknown Manufacturer'}</span>
                </div>
                ${report.datasheet_url && report.datasheet_url !== 'Not found' 
                    ? `<a href="${report.datasheet_url}" target="_blank" class="datasheet-btn">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                        Official Datasheet
                       </a>` : ''}
            </div>
            <p class="description" style="margin-top: 1.5rem; font-size: 1.2rem;">${report.description || 'No detailed description available.'}</p>
            <div class="report-header-grid" style="margin-top: 2rem;">
                <div class="spec-item"><span class="label">Package</span><span class="value">${report.package_type || 'N/A'}</span></div>
                <div class="spec-item"><span class="label">Voltage</span><span class="value">${report.operating_voltage || 'N/A'}</span></div>
                <div class="spec-item"><span class="label">Avg Price</span><span class="value">${report.price_range || 'N/A'}</span></div>
            </div>
        `;

        // 2. Render Pinout Box (with Zoom) and Table Fallback
        const pinWrapper = document.getElementById('pin-visual-wrapper');
        const tableWrapper = document.getElementById('table-container-wrapper');
        const imgUrl = report.image_url || 'https://via.placeholder.com/600x400?text=No+Pin+Diagram+Found';
        
        // Always render 2D image in the right box
        pinWrapper.innerHTML = `
            <img src="${imgUrl}" class="zoom-img" id="comp-img" style="width:100%; height:100%; min-height: 400px; object-fit:contain; background: rgba(0,0,0,0.2); border-radius: 8px;">
            <div id="zoom-lens"></div>
        `;
        pinWrapper.classList.remove('table-mode');
        setupImageZoom('comp-img', 'zoom-lens');

        if (report.key_pins_summary && report.key_pins_summary.length > 0) {
            // Render Table under 3D Model in the left box
            if (tableWrapper) {
                tableWrapper.innerHTML = `
                    <div class="pin-table-container" style="flex: 1; max-height: 300px; overflow-y: auto; margin-top: 1.5rem; border-top: 1px solid rgba(255,255,255,0.1);">
                        <table class="pin-summary-table">
                            <thead>
                                <tr>
                                    <th>Pin No.</th>
                                    <th>Name</th>
                                    <th>Function Description</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${report.key_pins_summary.map((pin, i) => `
                                    <tr>
                                        <td class="pin-no">${pin.pin_number || i + 1}</td>
                                        <td class="pin-name">${pin.pin_name || 'N/A'}</td>
                                        <td class="pin-desc">${(pin.function || 'N/A').replace(/[\u{1F300}-\u{1F9FF}]/gu, '')}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            }
        } else {
            if (tableWrapper) tableWrapper.innerHTML = '';
        }

        // 3. Render 3D Model Box
        initAdvanced3D(report);

        // 4. Render Pricing Box
        const pricingWrapper = document.getElementById('pricing-table-wrapper');
        pricingWrapper.innerHTML = `
            <div class="data-table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Distributor</th>
                            <th>Country</th>
                            <th>Unit Price</th>
                            <th>Availability</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${(report.pricing_breakdown || []).map(entry => `
                            <tr>
                                <td>${entry.distributor}</td>
                                <td>${entry.country}</td>
                                <td style="font-weight: 700; color: var(--primary);">${formatCurrency(entry.unit_price, entry.currency)}</td>
                                <td>${entry.stock_quantity.toLocaleString()} units</td>
                                <td><a href="${entry.url}" target="_blank" class="buy-link">Purchase Now</a></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        // 5. Render YouTube Tutorials natively extracting embed URLs
        const ytBox = document.getElementById('box-youtube');
        const ytWrapper = document.getElementById('youtube-tutorials-wrapper');
        
        if (report.youtube_links && report.youtube_links.length > 0) {
            ytBox.style.display = 'block';
            ytWrapper.innerHTML = report.youtube_links.map(link => {
                let videoId = '';
                if (link.includes('watch?v=')) {
                    videoId = link.split('watch?v=')[1].split('&')[0];
                } else if (link.includes('youtu.be/')) {
                    videoId = link.split('youtu.be/')[1].split('?')[0];
                }
                
                if (videoId) {
                    return `
                        <div class="yt-card" style="border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
                            <iframe width="100%" height="200" src="https://www.youtube.com/embed/${videoId}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                        </div>
                    `;
                }
                return '';
            }).join('');
        } else {
            ytBox.style.display = 'none';
        }

        setupTiltEffect();
    };

    const setupImageZoom = (imgID, lensID) => {
        const img = document.getElementById(imgID);
        const lens = document.getElementById(lensID);
        const container = img.parentElement;

        container.addEventListener('mousemove', (e) => {
            lens.style.display = 'block';
            const rect = container.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            // Positioning lens
            lens.style.left = `${x - 75}px`;
            lens.style.top = `${y - 75}px`;

            // Zoom background
            const ratio = 2.5;
            lens.style.backgroundImage = `url('${img.src}')`;
            lens.style.backgroundSize = `${img.width * ratio}px ${img.height * ratio}px`;
            lens.style.backgroundPosition = `-${x * ratio - 75}px -${y * ratio - 75}px`;
        });

        container.addEventListener('mouseleave', () => {
            lens.style.display = 'none';
        });
    };

    const initAdvanced3D = (report) => {
        const container = document.getElementById('canvas-container');
        if (!container) return;
        container.innerHTML = ''; // Clear previous

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(container.clientWidth, container.clientHeight);
        container.appendChild(renderer.domElement);
        
        // Raycaster Setup
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        const tooltip = document.getElementById('pin-tooltip');
        const pinMeshes = [];

        // Professional Lighting - NO DARK SHADOWS
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        scene.add(ambientLight);
        
        const hemiLight = new THREE.HemisphereLight(0xffffff, 0xffffff, 0.8);
        scene.add(hemiLight);
        
        const dirLight1 = new THREE.DirectionalLight(0xffffff, 1);
        dirLight1.position.set(5, 10, 7);
        scene.add(dirLight1);
        
        const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.6);
        dirLight2.position.set(-5, -5, -5); // Backlight to prevent any side from turning black
        scene.add(dirLight2);

        const chipGroup = new THREE.Group();
        const compName = (report.component_name || "").toUpperCase();
        const desc = (report.description || "").toUpperCase();
        const pkg = (report.package_type || "").toUpperCase();
        
        // Dynamic Board Detection
        const isModule = pkg.includes('MODULE') || pkg.includes('WROOM') || compName.includes('ESP32') || compName.includes('DRIVER') || desc.includes('DRIVER') || desc.includes('BOARD');

        // Dimensions (scaled down for WebGL coords)
        const dims = report.dimensions_mm || { length: 34.7, width: 7.5, height: 4.5 };
        let l = dims.length / 5;
        let w = dims.width / 5;
        const h = dims.height / 5;
        
        // Coerce dimensions for missing modules to look wider like flat PCBs
        if (isModule && dims.width === 7.5) {
            w = l * 0.9;
        }

        // Strict Material Palette - ONLY White, Green, Red, Yellow
        const mats = {
            base: new THREE.MeshPhongMaterial({ color: 0xffffff, shininess: 80 }), // Pure White base
            pcbGreen: new THREE.MeshPhongMaterial({ color: 0x00cc00, shininess: 20 }), // Green PCB
            metalCan: new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.5, roughness: 0.1 }), // White
            silverPin: new THREE.MeshStandardMaterial({ color: 0xffff00, metalness: 0.8, roughness: 0.1 }), // Yellow Pins
            hoverPin: new THREE.MeshBasicMaterial({ color: 0xff0000 }) // Pure Red hover
        };

        // Procedural Body & Texture Injection
        let bodyGeo;
        if (isModule) {
            // Flat board layout
            bodyGeo = new THREE.BoxGeometry(l, 0.2, w);
        } else {
            // Standard IC Resin Body
            bodyGeo = new THREE.BoxGeometry(l, h, w);
        }
        
        // Texture Mapping onto Top Face (Index 2 in BoxGeometry)
        const materialsList = [mats.base, mats.base, mats.base, mats.base, mats.base, mats.base];
        
        if (report.image_url) {
            const texLoader = new THREE.TextureLoader();
            texLoader.crossOrigin = "Anonymous";
            const tex = texLoader.load(report.image_url, undefined, undefined, function(err) {
                // If texture fails to load due to CORS or dead link, default back to white instead of black
                if (materialsList[2]) {
                    materialsList[2].map = null;
                    materialsList[2].needsUpdate = true;
                }
            });
            materialsList[2] = new THREE.MeshPhongMaterial({ map: tex, color: 0xffffff });
        }
        
        const bodyMesh = new THREE.Mesh(bodyGeo, materialsList);
        bodyMesh.position.y = isModule ? -0.1 : 0;
        chipGroup.add(bodyMesh);

        // Procedural Pin Integration
        const keyPins = report.key_pins_summary || [];
        
        // Extract exact physical pin count from package data (e.g. "DIP28" -> 28, "38-pin" -> 38)
        let totalPins = 8; // Generic default
        const pinMatch = pkg.match(/(\d+)/);
        if (pinMatch) {
            totalPins = parseInt(pinMatch[0], 10);
        }
        
        // Override component-specific exceptions if regex caught a model number instead of pin count
        if (compName.includes('ESP32')) totalPins = 38;
        if (totalPins < 2) totalPins = 8;
        
        let pinsPerSide = Math.ceil(totalPins / 2);
        let spacing = l / (pinsPerSide + 1);

        for (let i = 0; i < totalPins; i++) {
            const isLeft = i < pinsPerSide;
            const idxOnSide = isLeft ? i : (i - pinsPerSide);
            
            // Header pins point up for modules, DIP legs point down and out for ICs
            let pinLength = isModule ? 0.6 : (h * 1.2);
            const pinGeo = new THREE.BoxGeometry(0.2, pinLength, 0.2);
            const pinMesh = new THREE.Mesh(pinGeo, mats.silverPin.clone());
            
            const xPos = (idxOnSide * spacing) - (l / 2) + spacing;
            const zPos = isLeft ? -(w / 2) + (isModule ? 0.2 : -0.1) : (w / 2) - (isModule ? 0.2 : -0.1);
            const yPos = isModule ? 0.2 : -h / 4;

            pinMesh.position.set(xPos, yPos, zPos);
            if (!isModule && !isLeft) pinMesh.rotation.y = Math.PI; // flip pins for the other side
            
            // Map structured Pin Data securely
            const stringIndex = (i + 1).toString();
            let matchedPin = keyPins.find(p => {
                const nums = (p.pin_number || "").toString().split(',').map(s => s.trim());
                return nums.includes(stringIndex);
            });

            let mappedData;
            if (matchedPin) {
                mappedData = Object.assign({}, matchedPin, { pin_number: i + 1 }); 
            } else {
                mappedData = { pin_number: i+1, pin_name: `PIN ${i+1}`, function: "Standard Component Lead" };
            }

            pinMesh.userData = { pinData: mappedData, originalMat: pinMesh.material };
            
            pinMeshes.push(pinMesh);
            chipGroup.add(pinMesh);
        }

        scene.add(chipGroup);

        // Raycasting Logic for Tooltips
        container.addEventListener('mousemove', (e) => {
            const rect = container.getBoundingClientRect();
            mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
            
            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(pinMeshes);
            
            // Reset colors
            pinMeshes.forEach(p => p.material = p.userData.originalMat);

            if (intersects.length > 0) {
                const hoveredPin = intersects[0].object;
                hoveredPin.material = mats.hoverPin;
                
                const data = hoveredPin.userData.pinData;
                tooltip.style.display = 'block';
                tooltip.style.left = `${e.clientX + 10}px`;
                tooltip.style.top = `${e.clientY + 10}px`;
                tooltip.innerHTML = `
                    <div class="pin-title">PIN ${data.pin_number}: ${data.pin_name}</div>
                    <div class="pin-function">${data.function}</div>
                `;
                container.style.cursor = 'pointer';
            } else {
                tooltip.style.display = 'none';
                container.style.cursor = 'default';
            }
        });

        container.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
            pinMeshes.forEach(p => p.material = p.userData.originalMat);
        });

        // Advanced Scene Setup
        camera.position.set(5, 6, 8);
        camera.lookAt(0, 0, 0);

        const animate = () => {
            requestAnimationFrame(animate);
            chipGroup.rotation.y += 0.005; // Gentle rotation
            renderer.render(scene, camera);
        };
        animate();

        window.addEventListener('resize', () => {
            if (!container.clientWidth) return;
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        });
    };

    const formatCurrency = (val, cur) => {
        if (cur === 'INR') return `₹${val.toFixed(2)}`;
        if (cur === 'EUR') return `€${val.toFixed(2)}`;
        if (cur === 'GBP') return `£${val.toFixed(2)}`;
        return `$${val.toFixed(2)}`;
    };

    const setupTiltEffect = () => {
        const boxes = document.querySelectorAll('.glass-box:not(#box-header)');
        boxes.forEach(box => {
            box.addEventListener('mousemove', (e) => {
                const rect = box.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                
                // Reversed tilt so the pointer side comes to the front
                const rotateX = (y - centerY) / 15;
                const rotateY = (centerX - x) / 15;
                
                box.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
                box.style.boxShadow = `${-rotateY * 2}px ${rotateX * 2}px 40px -10px rgba(99, 102, 241, 0.3)`;
            });
            
            box.addEventListener('mouseleave', () => {
                box.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
                box.style.boxShadow = '0 10px 40px -10px rgba(0,0,0,0.5)';
            });
        });
    };

    // Event Listeners
    searchBtn.addEventListener('click', () => performSearch(input.value));
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performSearch(input.value);
    });

    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            const val = chip.getAttribute('data-val');
            input.value = val;
            performSearch(val);
        });
    });
});
