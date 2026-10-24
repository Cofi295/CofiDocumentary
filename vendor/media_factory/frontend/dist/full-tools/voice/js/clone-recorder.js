(() => {
  'use strict';

  const MIN_SECONDS = 3;
  const MAX_SECONDS = 10;
  const PROMPTS = {
    ko: [
      '오늘은 맑은 바람이 창문 사이로 들어옵니다. 저는 편안한 목소리로 이 문장을 천천히 읽고 있습니다.',
      '작은 변화가 새로운 기회를 만들기도 합니다. 지금 이 순간의 느낌을 자연스럽게 말해 보겠습니다.',
      '아침 햇살이 조용한 거리를 비추고 있습니다. 따뜻한 차 한 잔과 함께 하루를 시작합니다.',
      '멀리 보이는 산과 푸른 하늘이 마음을 편안하게 합니다. 오늘도 좋은 일이 생길 것 같습니다.',
      '사람마다 목소리에는 특별한 색깔이 있습니다. 저는 평소처럼 또렷하고 자연스럽게 이야기합니다.',
      '새로운 기술은 우리의 생활을 조금씩 바꾸고 있습니다. 중요한 것은 사람을 위한 방향을 찾는 일입니다.',
      '조용한 방에서 제 목소리에 집중해 봅니다. 너무 빠르지 않게 숨을 고르며 문장을 읽습니다.',
      '어제의 경험은 오늘의 지혜가 됩니다. 앞으로 나아가는 길에서 작은 배움을 소중히 여기겠습니다.'
    ],
    en: [
      'A gentle breeze is coming through the open window. I am reading these words clearly in my natural voice.',
      'Small changes can create wonderful new opportunities. I will speak calmly and let every phrase flow with ease.',
      'Morning sunlight is shining across the quiet street. A warm cup of tea helps me begin the day.',
      'The distant hills and bright blue sky feel peaceful today. I think something good may be waiting ahead.',
      'Every person has a unique color in their voice. I am speaking clearly, comfortably, and naturally.',
      'New technology slowly changes the way we live. The important part is choosing a direction that helps people.',
      'In this quiet room, I can focus on my voice. I breathe gently and read without rushing the words.',
      'Yesterday’s experience can become today’s wisdom. I value every small lesson as I continue moving forward.'
    ],
    vi: [
      'Một làn gió nhẹ đang đi qua khung cửa sổ. Tôi đọc những câu này thật rõ ràng bằng giọng nói tự nhiên của mình.',
      'Những thay đổi nhỏ có thể mở ra nhiều cơ hội mới. Tôi sẽ nói bình tĩnh để từng câu nối tiếp nhau nhẹ nhàng.',
      'Ánh nắng ban mai đang trải trên con phố yên tĩnh. Một tách trà ấm giúp tôi bắt đầu ngày mới.',
      'Dãy núi xa và bầu trời xanh mang lại cảm giác bình yên. Tôi tin rằng hôm nay sẽ có những điều tốt đẹp.',
      'Mỗi người đều có một màu sắc riêng trong giọng nói. Tôi đang nói rõ ràng, thoải mái và hoàn toàn tự nhiên.',
      'Công nghệ mới đang dần thay đổi cuộc sống hằng ngày. Điều quan trọng là lựa chọn hướng đi có ích cho con người.',
      'Trong căn phòng yên tĩnh này, tôi tập trung vào giọng nói. Tôi thở nhẹ và đọc từng câu mà không vội vàng.',
      'Kinh nghiệm của ngày hôm qua có thể trở thành hiểu biết hôm nay. Tôi trân trọng từng bài học nhỏ trên đường phía trước.'
    ]
  };

  class CloneRecorder {
    constructor({ onError, onStateChange }) {
      this.onError = onError;
      this.onStateChange = onStateChange;
      this.language = 'vi';
      this.lastPrompt = -1;
      this.mediaRecorder = null;
      this.stream = null;
      this.chunks = [];
      this.file = null;
      this.previewUrl = null;
      this.startedAt = 0;
      this.timer = null;
      this.autoStop = null;
      this.randomizePrompt();
    }

    setLanguage(code) {
      if (!PROMPTS[code]) {
        this.reset();
        this.language = code;
        return false;
      }
      if (code !== this.language) this.reset();
      this.language = code;
      this.randomizePrompt();
      return true;
    }

    randomizePrompt() {
      const choices = PROMPTS[this.language] || [];
      if (!choices.length) return '';
      this.resetRecordingOnly();
      let index = Math.floor(Math.random() * choices.length);
      if (choices.length > 1 && index === this.lastPrompt) index = (index + 1) % choices.length;
      this.lastPrompt = index;
      document.getElementById('record-prompt').textContent = choices[index];
      return choices[index];
    }

    getTranscript() { return document.getElementById('record-prompt').textContent.trim(); }
    getFile() { return this.file; }

    async start() {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        throw new Error('record_unsupported');
      }
      this.resetRecordingOnly();
      this.onStateChange('requesting_permission', 0);
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: 48000,
            noiseSuppression: true,
            echoCancellation: true,
            autoGainControl: true
          }
        });
        const mimeType = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus']
          .find(type => MediaRecorder.isTypeSupported(type)) || '';
        this.chunks = [];
        this.mediaRecorder = new MediaRecorder(this.stream, mimeType ? { mimeType } : undefined);
        this.mediaRecorder.ondataavailable = event => {
          if (event.data.size) this.chunks.push(event.data);
        };
        const activeRecorder = this.mediaRecorder;
        activeRecorder.onstop = () => this.finish(mimeType || activeRecorder.mimeType || 'audio/webm');
        activeRecorder.start(250);
        this.startedAt = performance.now();
        this.timer = setInterval(() => this.tick(), 100);
        this.autoStop = setTimeout(() => this.stop(true), MAX_SECONDS * 1000);
        this.onStateChange('recording', 0);
      } catch (_error) {
        this.stopTracks();
        this.onStateChange('idle', 0);
        throw new Error('record_permission');
      }
    }

    tick() {
      const elapsed = (performance.now() - this.startedAt) / 1000;
      this.onStateChange('recording', Math.min(MAX_SECONDS, elapsed));
    }

    stop(forced = false) {
      const elapsed = (performance.now() - this.startedAt) / 1000;
      if (!forced && elapsed < MIN_SECONDS) return false;
      if (this.mediaRecorder?.state === 'recording') this.mediaRecorder.stop();
      return true;
    }

    finish(mimeType) {
      clearInterval(this.timer);
      clearTimeout(this.autoStop);
      this.stopTracks();
      const elapsed = (performance.now() - this.startedAt) / 1000;
      if (elapsed < MIN_SECONDS) {
        this.onError('record_too_short');
        this.resetRecordingOnly();
        return;
      }
      const extension = mimeType.includes('ogg') ? 'ogg' : 'webm';
      const blob = new Blob(this.chunks, { type: mimeType });
      if (!blob.size) {
        this.onError('record_empty');
        this.resetRecordingOnly();
        return;
      }
      this.file = new File([blob], `microphone-reference.${extension}`, { type: mimeType });
      this.previewUrl = URL.createObjectURL(blob);
      this.onStateChange('preview', Math.min(MAX_SECONDS, elapsed), this.previewUrl);
    }

    stopTracks() {
      this.stream?.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    resetRecordingOnly() {
      clearInterval(this.timer);
      clearTimeout(this.autoStop);
      if (this.mediaRecorder?.state === 'recording') {
        this.mediaRecorder.onstop = null;
        this.mediaRecorder.stop();
      }
      this.stopTracks();
      if (this.previewUrl) URL.revokeObjectURL(this.previewUrl);
      this.mediaRecorder = null;
      this.file = null;
      this.previewUrl = null;
      this.chunks = [];
      this.onStateChange?.('idle', 0);
    }

    reset() { this.resetRecordingOnly(); }
    destroy() { this.resetRecordingOnly(); }
  }

  window.CloneRecorder = CloneRecorder;
})();
