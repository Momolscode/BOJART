// PCM only; no provider API and no network access in this processor.
class BojCapture extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const channel=inputs[0] && inputs[0][0];
    if(channel) this.port.postMessage(new Float32Array(channel));
    const out=outputs[0];if(out)for(const ch of out)ch.fill(0);
    return true;
  }
}
registerProcessor('boj-capture', BojCapture);
