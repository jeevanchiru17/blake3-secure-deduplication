/* src/api/static/app.js */
function init() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    
    const resultsSection = document.getElementById('results-section');
    
    // Chart instance
    let savingsChart = null;

    // Initial fetch for system stats
    initChart();
    fetchSystemStats();

    function initChart() {
        const ctx = document.getElementById('savingsChart').getContext('2d');
        savingsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Actual Storage Used', 'Storage Saved'],
                datasets: [{
                    data: [1, 0],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(16, 185, 129, 0.8)'
                    ],
                    borderColor: [
                        'rgba(59, 130, 246, 1)',
                        'rgba(16, 185, 129, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#f8fafc' }
                    }
                }
            }
        });
    }

    // User Keys Management
    let currentKeypair = null;
    let publicKeySpkiBase64 = null;
    
    const userSelect = document.getElementById('username-select');
    userSelect.addEventListener('change', () => {
        generateUserKeys(userSelect.value).then(fetchFileList).catch(err => {
            console.error("Failed in user select flow:", err);
        });
    });

    function showSecureContextWarning() {
        if (document.getElementById('secure-context-warning')) return;
        const warning = document.createElement('div');
        warning.id = 'secure-context-warning';
        warning.style.background = 'rgba(239, 68, 68, 0.2)';
        warning.style.border = '1px solid #ef4444';
        warning.style.color = '#fecaca';
        warning.style.padding = '1rem';
        warning.style.borderRadius = '0.75rem';
        warning.style.marginBottom = '1.5rem';
        warning.style.fontWeight = '600';
        warning.style.textAlign = 'left';
        warning.innerHTML = `
            ⚠️ <strong>Secure Context Required:</strong> The Web Crypto API is unavailable. 
            Please access this page via <a href="http://localhost:8000" style="color: #60a5fa; text-decoration: underline;">http://localhost:8000</a> 
            instead of IP addresses or other hostnames, or configure a secure HTTPS connection.
        `;
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(warning, container.firstChild);
        }
    }

    function checkCryptoSupport() {
        if (!window.crypto || !window.crypto.subtle) {
            console.error("Web Crypto API is not supported in this context.");
            showSecureContextWarning();
            return false;
        }
        return true;
    }

    async function generateUserKeys(username) {
        if (!checkCryptoSupport()) return;
        try {
            currentKeypair = await window.crypto.subtle.generateKey(
                { name: "ECDSA", namedCurve: "P-256" },
                true,
                ["sign", "verify"]
            );
            const exported = await window.crypto.subtle.exportKey("spki", currentKeypair.publicKey);
            publicKeySpkiBase64 = btoa(String.fromCharCode(...new Uint8Array(exported)));
            console.log(`Generated keys for ${username}`);
        } catch (err) {
            console.error("Key generation failed:", err);
            alert("Failed to generate cryptographic keys. Ensure you are accessing the page via localhost or HTTPS.");
        }
    }
    
    generateUserKeys(userSelect.value).then(fetchFileList).catch(err => {
        console.error("Initial key generation failed:", err);
    });

    // Make the entire drop zone clickable
    dropZone.addEventListener('click', (e) => {
        // Only click the input if we didn't click inside the label or the input itself (to avoid infinite loops)
        if (e.target !== fileInput && !e.target.closest('.btn-browse')) {
            fileInput.click();
        }
    });

    // Drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFileSelect, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }

    function handleFiles(files) {
        if (files.length > 0) {
            uploadFile(files[0]);
        }
    }

    async function uploadFile(file) {
        if (!currentKeypair) {
            if (!window.crypto || !window.crypto.subtle) {
                alert('Web Crypto API is not available in this browser/context. Please access this page using http://localhost:8000 to enable secure signing.');
            } else {
                alert('Keypair is not ready yet. Please wait a moment and try again.');
            }
            return;
        }

        progressContainer.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        progressBar.style.width = '0%';
        progressText.textContent = 'Signing file manifest...';

        const username = userSelect.value;
        const manifest = new TextEncoder().encode(`${file.name}:${file.size}`);
        
        const signatureBuffer = await window.crypto.subtle.sign(
            { name: "ECDSA", hash: {name: "SHA-256"} },
            currentKeypair.privateKey,
            manifest
        );
        const signatureBase64 = btoa(String.fromCharCode(...new Uint8Array(signatureBuffer)));

        const formData = new FormData();
        formData.append('username', username);
        formData.append('public_key', publicKeySpkiBase64);
        formData.append('signature', signatureBase64);
        formData.append('file', file);

        progressText.textContent = 'Uploading and Deduplicating...';

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);

        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressBar.style.width = percentComplete + '%';
            }
        };

        xhr.onload = function() {
            if (xhr.status === 200) {
                const response = JSON.parse(xhr.responseText);
                displayResults(response);
                fetchSystemStats();
                fetchFileList();
                progressContainer.classList.add('hidden');
            } else {
                alert('Upload failed. ' + xhr.responseText);
                progressContainer.classList.add('hidden');
            }
        };

        xhr.onerror = function() {
            alert('Upload error.');
            progressContainer.classList.add('hidden');
        };

        xhr.send(formData);
    }

    function displayResults(data) {
        resultsSection.classList.remove('hidden');
        
        document.getElementById('res-filename').textContent = data.filename;
        document.getElementById('res-chunks').textContent = data.chunks_processed;
        document.getElementById('res-dupes').textContent = data.duplicate_chunks;
        
        // Format percentage
        const savedPct = data.storage_saved_percent.toFixed(1);
        document.getElementById('res-saved').textContent = savedPct + '%';
        
        document.getElementById('res-hash').textContent = data.file_hash;
        
        const badge = document.getElementById('res-badge');
        if (data.duplicate_chunks > 0) {
            badge.textContent = 'Duplicate Found';
            badge.className = 'badge duplicate';
            document.getElementById('res-dupes').classList.add('highlight');
        } else {
            badge.textContent = 'New File Stored';
            badge.className = 'badge';
            document.getElementById('res-dupes').classList.remove('highlight');
        }
    }

    function fetchSystemStats() {
        fetch('/system-stats')
            .then(res => res.json())
            .then(data => {
                document.getElementById('sys-files').textContent = data.total_files;
                document.getElementById('sys-raw').textContent = formatBytes(data.raw_total_size);
                document.getElementById('sys-actual').textContent = formatBytes(data.unique_storage_used);
                document.getElementById('sys-saved-pct').textContent = data.storage_saved_percent.toFixed(1) + '%';
                
                if (savingsChart) {
                    savingsChart.data.datasets[0].data = [
                        data.unique_storage_used || 1,
                        data.bytes_saved || 0
                    ];
                    savingsChart.update();
                }
            })
            .catch(err => console.error('Error fetching stats:', err));
    }

    function formatBytes(bytes, decimals = 2) {
        if (!+bytes) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    }

    function fetchFileList() {
        const username = userSelect.value;
        fetch(`/files?username=${encodeURIComponent(username)}`)
            .then(res => res.json())
            .then(files => {
                const tbody = document.getElementById('file-list');
                if (!tbody) return;
                tbody.innerHTML = '';
                files.forEach(file => {
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
                    
                    const date = new Date(file.upload_date).toLocaleString();
                    const sizeStr = formatBytes(file.total_size);
                    
                    tr.innerHTML = `
                        <td style="padding: 0.75rem 0;">${file.filename}</td>
                        <td style="padding: 0.75rem 0;">${sizeStr}</td>
                        <td style="padding: 0.75rem 0; color: var(--text-secondary); font-size: 0.9rem;">${date}</td>
                        <td style="padding: 0.75rem 0; text-align: right;">
                            <a href="/download/${file.id}?username=${encodeURIComponent(username)}" target="_blank" class="btn-browse" style="padding: 0.4rem 0.8rem; font-size: 0.85rem; text-decoration: none;">Download</a>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            })
            .catch(err => console.error('Error fetching file list:', err));
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
