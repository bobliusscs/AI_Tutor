/**
 * 音频队列播放器
 * 支持按序播放乱序到达的音频分片，无缝衔接
 */
export class AudioQueuePlayer {
  constructor() {
    this.queue = new Map()    // Map<index, {audioBase64, mimeType}>
    this.nextPlayIndex = 0    // 下一个要播放的分片索引
    this.playing = false      // 是否正在播放
    this.stopped = false      // 是否已停止
    this.completed = false    // 是否所有分片都已到达
    this.totalChunks = -1     // 总分片数（-1表示未知）
    this.currentAudio = null  // 当前播放的Audio对象
    this._onStateChange = null
    this._onPlaybackComplete = null
  }

  /**
   * 触发状态变更回调
   * @private
   */
  _emitStateChange() {
    if (this._onStateChange) {
      this._onStateChange({
        playing: this.playing,
        currentIndex: this.nextPlayIndex,
        stopped: this.stopped
      })
    }
  }

  /**
   * 将音频分片加入队列
   * @param {number} index - 分片索引（保证播放顺序）
   * @param {string} audioBase64 - base64编码的音频数据
   * @param {string} format - 音频格式，如 'mp3'、'wav'
   */
  enqueue(index, audioBase64, format) {
    if (this.stopped) return
    if (this.queue.has(index)) return
    // 根据音频格式映射 MIME 类型，默认 wav
    const mimeType = format === 'mp3' ? 'audio/mpeg' : 'audio/wav'
    this.queue.set(index, { audioBase64, mimeType })
    // 如果还没开始播放，自动开始
    if (!this.playing && !this.stopped) {
      this.startPlayback()
    }
  }

  /**
   * 播放指定索引的音频分片
   * @param {number} index - 分片索引
   * @private
   */
  async _playChunk(index) {
    const chunkData = this.queue.get(index)
    if (!chunkData) {
      return false
    }

    const { audioBase64, mimeType } = chunkData
    if (!audioBase64) {
      return false
    }

    return new Promise((resolve) => {
      try {
        const audio = new Audio(`data:${mimeType || 'audio/mpeg'};base64,${audioBase64}`)
        this.currentAudio = audio

        audio.onended = () => {
          this.currentAudio = null
          this.queue.delete(index)
          this.nextPlayIndex = index + 1
          this._emitStateChange()
          resolve(true)
        }

        audio.onerror = () => {
          console.warn(`音频分片 ${index} 播放失败，跳过`)
          this.currentAudio = null
          this.queue.delete(index)
          this.nextPlayIndex = index + 1
          this._emitStateChange()
          resolve(true) // 即使失败也继续
        }

        audio.play().catch((err) => {
          console.warn(`音频分片 ${index} 播放异常:`, err)
          this.currentAudio = null
          this.queue.delete(index)
          this.nextPlayIndex = index + 1
          this._emitStateChange()
          resolve(true)
        })
      } catch (err) {
        console.warn(`音频分片 ${index} 创建失败:`, err)
        this.currentAudio = null
        this.queue.delete(index)
        this.nextPlayIndex = index + 1
        this._emitStateChange()
        resolve(true)
      }
    })
  }

  /**
   * 尝试播放下一个分片
   * @private
   */
  async _playNext() {
    if (this.stopped) {
      this.playing = false
      this._emitStateChange()
      return
    }

    // 检查是否所有分片已播放完
    if (this.totalChunks !== -1 && this.nextPlayIndex >= this.totalChunks) {
      this.playing = false
      this._emitStateChange()
      if (this._onPlaybackComplete) this._onPlaybackComplete()
      return
    }

    // 等待下一个分片就绪（轮询，最多等 30 秒）
    let waitCount = 0
    while (!this.queue.has(this.nextPlayIndex) && !this.stopped && waitCount < 300) {
      // 如果已标记完成且当前索引超出，退出
      if (this.totalChunks !== -1 && this.nextPlayIndex >= this.totalChunks) {
        this.playing = false
        this._emitStateChange()
        if (this._onPlaybackComplete) this._onPlaybackComplete()
        return
      }
      await new Promise(r => setTimeout(r, 100))
      waitCount++
    }

    if (this.stopped || !this.queue.has(this.nextPlayIndex)) {
      this.playing = false
      this._emitStateChange()
      if (this.completed && this._onPlaybackComplete) {
        this._onPlaybackComplete()
      }
      return
    }

    // 播放当前分片
    this.playing = true
    this._emitStateChange()
    const success = await this._playChunk(this.nextPlayIndex)
    if (success && !this.stopped) {
      this._playNext()
    }
  }

  /**
   * 开始播放队列
   * 如果已在播放中则忽略
   */
  async startPlayback() {
    // 防重复播放
    if (this.playing) {
      return
    }

    // 已停止则不能开始
    if (this.stopped) {
      return
    }

    // 开始播放
    await this._playNext()
  }

  /**
   * 停止播放并清空队列
   */
  stop() {
    this.stopped = true

    // 立即停止当前播放
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio.currentTime = 0
      this.currentAudio = null
    }

    this.playing = false
    this._emitStateChange()
  }

  /**
   * 标记所有分片已发送完毕
   * @param {number} total - 总分片数
   */
  markComplete(total) {
    this.completed = true
    this.totalChunks = total

    // 如果根本没有任何分片到达，直接结束
    if (this.queue.size === 0 && this.nextPlayIndex === 0) {
      this.playing = false
      this._emitStateChange()
      if (this._onPlaybackComplete) this._onPlaybackComplete()
      return
    }

    // 如果当前没有在播放且还有未播放的分片，尝试继续播放
    if (!this.playing && !this.stopped) {
      this.startPlayback()
    }

    // 检查是否所有分片都已播放完毕
    if (this.nextPlayIndex >= this.totalChunks) {
      this.playing = false
      this._emitStateChange()
      if (this._onPlaybackComplete) this._onPlaybackComplete()
    }
  }

  /**
   * 设置状态变更回调
   * @param {function} callback - (state: {playing, currentIndex, stopped}) => void
   */
  onStateChange(callback) {
    this._onStateChange = callback
  }

  /**
   * 设置播放完成回调
   * @param {function} callback - () => void
   */
  onPlaybackComplete(callback) {
    this._onPlaybackComplete = callback
  }

  /**
   * 重置播放器状态（新一轮对话时调用）
   */
  reset() {
    // 停止当前播放
    if (this.currentAudio) {
      this.currentAudio.pause()
      this.currentAudio.currentTime = 0
      this.currentAudio = null
    }

    // 清空队列
    this.queue.clear()

    // 重置状态
    this.nextPlayIndex = 0
    this.playing = false
    this.stopped = false
    this.completed = false
    this.totalChunks = -1
    this._onStateChange = null
    this._onPlaybackComplete = null
  }
}

export default AudioQueuePlayer
