       
        let currentTaskId = null;
        let audioData = null;
        let currentStep = 'initial'; // 'initial', 'processing', 'completed', 'sending'
        let autoUpload = true; // Rastrear el estado del checkbox

        const form = document.getElementById('audioForm');
        const container = document.getElementById('mainContainer');
        const statusCard = document.getElementById('statusCard');
        const additionalFields = document.getElementById('additionalFields');
        const mainBtn = document.getElementById('mainBtn');
        const btnText = document.getElementById('btnText');
        const loadingSpinner = document.getElementById('loadingSpinner');
        const resetBtn = document.getElementById('resetBtn');
        const actionButtons = document.getElementById('actionButtons');
        const downloadBtn = document.getElementById('downloadBtn');
        const sendBtn = document.getElementById('sendBtn');
        const autoUploadCheckbox = document.getElementById('autoUploadCheckbox');

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (currentStep === 'initial') {
                autoUpload = autoUploadCheckbox ? autoUploadCheckbox.checked : true;
                await startAudioDownload();
            }
        });

        downloadBtn.addEventListener('click', async function() {
            await downloadAudio();
        });

        sendBtn.addEventListener('click', async function() {
            await sendToExternal();
        });

        // Función para verificar conectividad del servidor externo
        async function checkExternalServerConnectivity() {
            if (!externalApiUrl || externalApiUrl.trim() === "") {
                return false;
            }
            
            try {
                // Intentar hacer un HEAD request o GET para verificar conectividad
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 segundos timeout
                
                const response = await fetch(externalApiUrl, {
                    method: 'HEAD',
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                return response.status < 500; // Cualquier respuesta que no sea error del servidor
                
            } catch (error) {
                return false;
            }
        }

        // Función para mostrar estado de conectividad
        async function updateServerStatus() {
            if (!externalApiUrl || externalApiUrl.trim() === "") {
                return;
            }
            
            const isConnected = await checkExternalServerConnectivity();
            const sendBtn = document.getElementById('sendBtn');
            
            if (!isConnected) {
                sendBtn.textContent = 'Servidor No Disponible';
                sendBtn.style.backgroundColor = '#dc3545';
                sendBtn.title = 'El servidor externo no está disponible. Haz clic para reintentar.';
            } else {
                sendBtn.textContent = 'Enviar al Servidor';
                sendBtn.style.backgroundColor = '';
                sendBtn.title = '';
            }
        }

        async function startAudioDownload() {
            const url = document.getElementById('videoUrl').value;
            
            currentStep = 'processing';
            updateUI();
            
            try {
                // Iniciar descarga de audio usando el endpoint /audio
                const response = await fetch(`/audio?url=${encodeURIComponent(url)}`, {
                    method: 'GET'
                });
                
                const data = await response.json();
                
                if (data.task_id) {
                    currentTaskId = data.task_id;
                    checkTaskStatus(data.task_id, url);
                } else {
                    throw new Error('No se pudo iniciar la descarga');
                }
            } catch (error) {
                showError('Error al iniciar la descarga: ' + error.message);
                currentStep = 'initial';
                updateUI();
            }
        }

        async function checkTaskStatus(taskId, originalUrl) {
            try {
                const response = await fetch(`/task/${taskId}`);
                const data = await response.json();
                
                if (data.status === 'processing') {
                    document.getElementById('statusText').textContent = 'Descargando y convirtiendo audio...';
                    setTimeout(() => checkTaskStatus(taskId, originalUrl), 5000);
                } else if (data.status === 'completed') {
                    audioData = data.result;
                    showCompletedState(data.result, originalUrl);
                } else if (data.status === 'error') {
                    showError('Error en la descarga: ' + data.error);
                }
            } catch (error) {
                showError('Error al verificar el estado: ' + error.message);
            }
        }

        function showCompletedState(result, originalUrl) {
            currentStep = 'completed';
            
            // Llenar campos
            document.getElementById('title').value = result.title;
            document.getElementById('url').value = originalUrl;
            document.getElementById('filename').value = result.file_name;
            
            // Mostrar estado de éxito
            statusCard.classList.add('success');
            document.getElementById('statusText').textContent = '¡Audio descargado exitosamente!';
            
            // Si autoUpload está habilitado
            if (autoUpload && externalApiUrl && externalApiUrl.trim() !== "") {
                // Enviar automáticamente al servidor
                sendToExternal();
            } else {
                // Mostrar botones de acción si no es auto-upload o no hay servidor
                actionButtons.classList.remove('hidden');
                downloadBtn.classList.remove('hidden');
                
                // Si external_api_url existe, mostrar campos adicionales y botón de envío
                if (externalApiUrl && externalApiUrl.trim() !== "") {
                    // Expandir contenedor y mostrar campos adicionales
                    container.classList.add('expanded');
                    additionalFields.classList.add('show');
                    sendBtn.classList.remove('hidden');
                    
                    // Verificar estado del servidor externo
                    updateServerStatus();
                }
            }
            
            updateUI();
        }

        async function downloadAudio() {
            if (!audioData || !audioData.file_name) {
                showError('No hay archivo de audio disponible para descargar');
                return;
            }
            
            try {
                // Crear un enlace temporal para descargar el archivo
                const response = await fetch(`/get-audio-file/${audioData.file_name}`);
                if (!response.ok) {
                    throw new Error('Error al obtener el archivo de audio');
                }
                
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = audioData.file_name;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                
                showSuccess('¡Audio descargado exitosamente!');
            } catch (error) {
                showError('Error al descargar el audio: ' + error.message);
            }
        }

        async function sendToExternal() {
            currentStep = 'sending';
            updateUI();
            
            try {
                // Verificar que la URL externa esté configurada
                if (!externalApiUrl || externalApiUrl.trim() === "") {
                    throw new Error('URL del servidor externo no configurada');
                }
                
                const formData = new FormData();
                formData.append('title', document.getElementById('title').value);
                formData.append('url', document.getElementById('url').value);
                formData.append('filename', document.getElementById('filename').value);
                
                // Obtener el archivo de audio
                const audioResponse = await fetch(`/get-audio-file/${audioData.file_name}`);
                if (!audioResponse.ok) {
                    throw new Error('No se pudo obtener el archivo de audio');
                }
                const audioBlob = await audioResponse.blob();
                formData.append('audio_file', audioBlob, audioData.file_name);
                
                // Configurar timeout para la petición
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 segundos timeout
                
                try {
                    const response = await fetch(`${externalApiUrl}`, {
                        method: 'POST',
                        body: formData,
                        signal: controller.signal
                    });
                    
                    clearTimeout(timeoutId);
                    
                    if (!response.ok) {
                        // Intentar obtener el mensaje de error del servidor
                        let errorMessage = 'Error desconocido del servidor';
                        try {
                            const errorData = await response.json();
                            errorMessage = errorData.error || errorData.message || `Error ${response.status}: ${response.statusText}`;
                        } catch (parseError) {
                            errorMessage = `Error ${response.status}: ${response.statusText}`;
                        }
                        throw new Error(errorMessage);
                    }
                    
                    const result = await response.json();
                    
                    // Si fue automático, solo mostrar el resultado
                    if (autoUpload) {
                        showSuccess('¡Audio descargado y enviado exitosamente al servidor!');
                    } else {
                        showSuccess('¡Datos enviados exitosamente al sistema externo!');
                    }
                    
                } catch (fetchError) {
                    clearTimeout(timeoutId);
                    
                    if (fetchError.name === 'AbortError') {
                        throw new Error('Timeout: El servidor externo no responde. Verifica que esté disponible.');
                    } else if (fetchError.message.includes('ERR_CONNECTION_REFUSED') || 
                              fetchError.message.includes('Failed to fetch') ||
                              fetchError.name === 'TypeError') {
                        throw new Error('No se puede conectar al servidor externo. Verifica que esté ejecutándose y accesible.');
                    } else {
                        throw fetchError;
                    }
                }
                
            } catch (error) {
                let errorMessage = error.message;
                
                // Personalizar mensajes de error comunes
                if (error.message.includes('NetworkError') || error.message.includes('fetch')) {
                    errorMessage = 'Error de conexión: No se puede conectar al servidor externo. Verifica tu conexión a internet y que el servidor esté disponible.';
                } else if (error.message.includes('TypeError: Failed to fetch')) {
                    errorMessage = 'Servidor externo no disponible: Verifica que el servidor esté ejecutándose y la URL sea correcta.';
                }
                
                showError('Error al enviar datos: ' + errorMessage, false);
                
                // Si fue automático y hubo error, mostrar botones de reintento
                if (autoUpload) {
                    actionButtons.classList.remove('hidden');
                    downloadBtn.classList.remove('hidden');
                    container.classList.add('expanded');
                    additionalFields.classList.add('show');
                    sendBtn.classList.remove('hidden');
                }
                
                // Actualizar estado del botón después del error
                setTimeout(() => {
                    updateServerStatus();
                }, 1000);
                
                // Cambiar el step de vuelta a completed para permitir reintento
                currentStep = 'completed';
                
            } finally {
                // Restaurar estado de los botones
                sendBtn.disabled = false;
                sendBtn.textContent = 'Enviar al Servidor';
                downloadBtn.disabled = false;
            }
        }

        function updateUI() {
            switch(currentStep) {
                case 'initial':
                    btnText.textContent = 'Enviar';
                    mainBtn.disabled = false;
                    loadingSpinner.classList.add('hidden');
                    statusCard.classList.remove('show');
                    resetBtn.classList.add('hidden');
                    actionButtons.classList.add('hidden');
                    break;
                    
                case 'processing':
                    btnText.textContent = 'Procesando...';
                    mainBtn.disabled = true;
                    loadingSpinner.classList.remove('hidden');
                    statusCard.classList.add('show');
                    statusCard.classList.remove('success', 'error');
                    actionButtons.classList.add('hidden');
                    break;
                    
                case 'completed':
                    mainBtn.style.display = 'none';
                    loadingSpinner.classList.add('hidden');
                    resetBtn.classList.remove('hidden');
                    break;
                    
                case 'sending':
                    sendBtn.disabled = true;
                    sendBtn.textContent = 'Enviando...';
                    sendBtn.style.backgroundColor = '';
                    sendBtn.title = '';
                    downloadBtn.disabled = true;
                    break;
            }
        }

        function showError(message, resetToInitial = true) {
            statusCard.classList.add('show', 'error');
            statusCard.classList.remove('success');
            document.getElementById('statusText').textContent = message;
            
            if (resetToInitial) {
                currentStep = 'initial';
                updateUI();
            }
        }

        function showSuccess(message) {
            statusCard.classList.add('show', 'success');
            statusCard.classList.remove('error');
            document.getElementById('statusText').textContent = message;
            resetBtn.classList.remove('hidden');
            mainBtn.style.display = 'none';
        }

        function resetForm() {
            // Reset estado
            currentStep = 'initial';
            currentTaskId = null;
            audioData = null;
            
            // Limpiar formulario
            form.reset();
            
            // Ocultar elementos
            statusCard.classList.remove('show', 'success', 'error');
            additionalFields.classList.remove('show');
            container.classList.remove('expanded');
            resetBtn.classList.add('hidden');
            actionButtons.classList.add('hidden');
            mainBtn.style.display = 'block';
            
            // Restaurar estado de botones
            sendBtn.disabled = false;
            sendBtn.textContent = 'Enviar al Servidor';
            sendBtn.style.backgroundColor = '';
            sendBtn.title = '';
            downloadBtn.disabled = false;
            
            updateUI();
        }

        // Auto-submit al pegar URL (opcional)
        document.getElementById('videoUrl').addEventListener('paste', function(e) {
            setTimeout(() => {
                const url = this.value;
                if (url && (url.includes('youtube.com') || url.includes('youtu.be')) && currentStep === 'initial') {
                    // Auto-submit después de 1 segundo si no hay cambios
                    setTimeout(() => {
                        if (currentStep === 'initial' && this.value === url) {
                            form.dispatchEvent(new Event('submit'));
                        }
                    }, 1500);
                }
            }, 200);
        });