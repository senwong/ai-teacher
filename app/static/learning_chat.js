(() => {
  const root = document.querySelector('[data-learning-chat]');
  if (!root) return;

  const form = root.querySelector('[data-chat-form]');
  const input = root.querySelector('[data-chat-input]');
  const messages = root.querySelector('[data-chat-messages]');
  const micButton = root.querySelector('[data-mic-button]');
  const micStatus = root.querySelector('[data-mic-status]');
  const autoSpeakToggle = root.querySelector('[data-auto-speak]');
  const rateSelect = root.querySelector('[data-speech-rate]');
  const stopButton = root.querySelector('[data-speech-stop]');
  const replayButton = root.querySelector('[data-speech-replay]');
  const submitButton = root.querySelector('[data-chat-submit]');
  const suggestionButtons = root.querySelectorAll('[data-chat-suggestion]');
  const teachingContent = document.querySelector('[data-teaching-content]');
  const initialSpeech = teachingContent ? teachingContent.innerText.trim() : '';

  let lastSpokenText = '';
  let recognition = null;
  let socket = null;
  let reconnectTimer = null;
  let reconnectAttempt = 0;
  let pingTimer = null;
  let closing = false;
  let waitingForAnswer = false;

  const connectionStatus = document.createElement('div');
  connectionStatus.className = 'meta';
  connectionStatus.style.marginBottom = '10px';
  form.parentNode.insertBefore(connectionStatus, form);

  const autoSpeakKey = 'aiTeacherAutoSpeak';
  const speechRateKey = 'aiTeacherSpeechRate';
  const savedAutoSpeak = localStorage.getItem(autoSpeakKey);
  const savedRate = localStorage.getItem(speechRateKey);
  autoSpeakToggle.checked = savedAutoSpeak === null ? true : savedAutoSpeak === 'true';
  if (savedRate && rateSelect.querySelector(`option[value="${savedRate}"]`)) {
    rateSelect.value = savedRate;
  }

  function setConnectionStatus(text) {
    connectionStatus.textContent = text;
  }

  function resetSubmitButton() {
    waitingForAnswer = false;
    submitButton.disabled = false;
    submitButton.textContent = '问老师';
    input.focus();
  }

  function speak(text, force = false) {
    if (!('speechSynthesis' in window) || !text) return;
    if (!force && !autoSpeakToggle.checked) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN';
    utterance.rate = Number(rateSelect.value || '1');
    lastSpokenText = text;
    window.speechSynthesis.speak(utterance);
  }

  function appendMessage(role, text) {
    const item = document.createElement('div');
    item.className = `chat-message ${role === 'student' ? 'chat-message-student' : 'chat-message-teacher'}`;

    const label = document.createElement('strong');
    label.textContent = role === 'student' ? '你' : 'AI 老师';
    const content = document.createElement('p');
    content.textContent = text;

    item.append(label, content);
    messages.appendChild(item);
    item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function websocketUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const params = new URLSearchParams({ session_id: root.dataset.sessionId });
    return `${protocol}//${window.location.host}/ws/learn/chat?${params.toString()}`;
  }

  function startPing() {
    clearInterval(pingTimer);
    pingTimer = setInterval(() => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping' }));
      }
    }, 25000);
  }

  function scheduleReconnect() {
    if (closing || reconnectTimer) return;
    const delay = Math.min(1000 * (2 ** reconnectAttempt), 5000);
    reconnectAttempt += 1;
    setConnectionStatus(`老师连接断开，${Math.round(delay / 1000)} 秒后重连…`);
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectWebSocket();
    }, delay);
  }

  function connectWebSocket() {
    if (closing) return;
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;

    setConnectionStatus('正在连接 AI 老师…');
    socket = new WebSocket(websocketUrl());

    socket.addEventListener('open', () => {
      reconnectAttempt = 0;
      setConnectionStatus('AI 老师已连接 · WebSocket');
      startPing();
    });

    socket.addEventListener('message', (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (_) {
        return;
      }

      if (payload.type === 'connected' || payload.type === 'pong') return;
      if (payload.type === 'thinking') {
        waitingForAnswer = true;
        submitButton.disabled = true;
        submitButton.textContent = '老师正在想…';
        return;
      }
      if (payload.type === 'answer') {
        appendMessage('teacher', payload.answer);
        speak(payload.answer);
        resetSubmitButton();
        return;
      }
      if (payload.type === 'error') {
        appendMessage('teacher', payload.detail || '老师暂时无法回答，请再试一次。');
        resetSubmitButton();
      }
    });

    socket.addEventListener('close', (event) => {
      clearInterval(pingTimer);
      socket = null;
      if (waitingForAnswer) {
        appendMessage('teacher', '连接刚刚中断了，请重新发送这个问题。');
        resetSubmitButton();
      }
      if (!closing) {
        if (event.code === 4401) setConnectionStatus('学生登录已失效，请重新登录。');
        else if (event.code === 4404) setConnectionStatus('当前学习 Session 已失效，请重新开始学习。');
        else scheduleReconnect();
      }
    });

    socket.addEventListener('error', () => {
      setConnectionStatus('AI 老师连接出现问题，正在重试…');
    });
  }

  function submitQuestion(question) {
    const text = (question || input.value).trim();
    if (!text || submitButton.disabled) return;

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setConnectionStatus('AI 老师正在重新连接，请稍后再问。');
      connectWebSocket();
      return;
    }

    appendMessage('student', text);
    input.value = '';
    waitingForAnswer = true;
    submitButton.disabled = true;
    submitButton.textContent = '发送中…';
    socket.send(JSON.stringify({ type: 'chat', message: text }));
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    submitQuestion();
  });

  suggestionButtons.forEach((button) => {
    button.addEventListener('click', () => {
      input.value = button.dataset.chatSuggestion;
      input.focus();
    });
  });

  autoSpeakToggle.addEventListener('change', () => {
    localStorage.setItem(autoSpeakKey, String(autoSpeakToggle.checked));
    if (!autoSpeakToggle.checked && 'speechSynthesis' in window) window.speechSynthesis.cancel();
  });

  rateSelect.addEventListener('change', () => {
    localStorage.setItem(speechRateKey, rateSelect.value);
  });

  stopButton.addEventListener('click', () => {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  });

  replayButton.addEventListener('click', () => speak(lastSpokenText || initialSpeech, true));

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (Recognition) {
    recognition = new Recognition();
    recognition.lang = 'zh-CN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      micButton.textContent = '⏹ 停止';
      micStatus.textContent = '正在听你说…';
    };
    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      input.value = text;
      micStatus.textContent = '已经转成文字，可以修改后再发送。';
      input.focus();
    };
    recognition.onerror = () => {
      micStatus.textContent = '没有听清，可以再说一次或直接打字。';
    };
    recognition.onend = () => {
      micButton.textContent = '🎤 说话';
    };

    micButton.addEventListener('click', () => {
      try {
        if (micButton.textContent.includes('停止')) recognition.stop();
        else recognition.start();
      } catch (_) {
        micStatus.textContent = '麦克风正在使用，请稍后再试。';
      }
    });
  } else {
    micButton.disabled = true;
    micButton.textContent = '🎤 当前浏览器不支持';
    micStatus.textContent = '可以继续使用文字提问。';
  }

  if (!('speechSynthesis' in window)) {
    autoSpeakToggle.checked = false;
    autoSpeakToggle.disabled = true;
    rateSelect.disabled = true;
    stopButton.disabled = true;
    replayButton.disabled = true;
  } else if (initialSpeech && autoSpeakToggle.checked) {
    setTimeout(() => speak(initialSpeech), 350);
  }

  window.addEventListener('beforeunload', () => {
    closing = true;
    clearTimeout(reconnectTimer);
    clearInterval(pingTimer);
    if (socket) socket.close(1000, 'page closed');
  });

  connectWebSocket();
})();
