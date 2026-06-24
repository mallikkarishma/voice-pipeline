class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.bufferSize = 4096;
    this.buffer = new Float32Array(this.bufferSize);
    this.bufferIndex = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (input.length > 0) {
      const channelData = input[0];
      for (let i = 0; i < channelData.length; i++) {
        this.buffer[this.bufferIndex++] = channelData[i];
        if (this.bufferIndex >= this.bufferSize) {
          this.flush();
        }
      }
    }
    return true;
  }

  flush() {
    let sumSquares = 0;
    const pcm16 = new Int16Array(this.bufferIndex);
    for (let i = 0; i < this.bufferIndex; i++) {
      const sample = this.buffer[i];
      sumSquares += sample * sample;
      const clipped = Math.max(-1, Math.min(1, sample));
      pcm16[i] = clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff;
    }
    const rms = Math.sqrt(sumSquares / this.bufferIndex);
    this.port.postMessage({ pcm: pcm16.buffer, rms }, [pcm16.buffer]);
    this.bufferIndex = 0;
  }
}

registerProcessor("pcm-processor", PCMProcessor);