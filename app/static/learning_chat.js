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
  const initialSpeech = root.dataset.initialSpeech || '';

  let lastSpokenText = '';
  let recognition = null;

  const autoSpeakKey = 'aiTeacherAutoSpeak';
  const speechRateKey = 'aiTeacherSpeechRate';
  const savedAutoSpeak = localStorage.getItem(autoSpeakKey);
  const savedRate = localStorage.getItem(speechRateKey);
  autoSpeakToggle.checked = savedAutoSpeak === null ? true : savedAutoSpeak === 'true';
  if (savedRate && rateSelect.querySelector(`option[value="${savedRate}"]`)) {
    rateSelect.value = savedRate;
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

  async function submitQuestion(question) {
    const text = (question || input.value).trim();
    if (!text || submitButton.disabled) return;

    appendMessage('student', text);
    input.value = '';
    submitButton.disabled = true;
    submitButton.textContent = '老师正在想…';

    const data = new URLSearchParams();
    data.set('session_id', root.dataset.sessionId);
    data.set('message', text);

    try {
      const response = await fetch('/learn/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
        body: data.toString(),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || '老师暂时没有听清，请再试一次。');
      appendMessage('teacher', payload.answer);
      speak(payload.answer);
    } catch (error) {
      appendMessage('teacher', error.message || '老师暂时无法回答，请稍后再试。');
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = '问老师';
      input.focus();
    }
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
    // Some browsers may require a user gesture before speaking; if blocked,
    // the replay button remains available.
    setTimeout(() => speak(initialSpeech), 350);
  }
})();
