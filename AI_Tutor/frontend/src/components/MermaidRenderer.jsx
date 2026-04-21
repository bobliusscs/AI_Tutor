import React, { useEffect, useState, useRef, useCallback } from 'react';
import { FullscreenOutlined, FullscreenExitOutlined, DownloadOutlined } from '@ant-design/icons';

let idCounter = 0;

// 检测 Mermaid 代码是否完整（用于流式输出场景）
const isMermaidComplete = (code) => {
  if (!code) return false;

  // 检查是否有 mermaid 图表类型声明
  const hasOpen = code.trim().match(/^(flowchart|graph|mindmap|sequenceDiagram|gantt|classDiagram|erDiagram|stateDiagram|pie|quadrantChart|requirement|gitGraph|xychart)/im);

  // 有代码块标记的情况：检查反引号配对
  if (/```mermaid/i.test(code)) {
    const backtickCount = (code.match(/```/g) || []).length;
    return backtickCount >= 2 && backtickCount % 2 === 0;
  }

  // 无代码块标记的情况
  const trimmed = code.trim();

  // 检查括号配对（包括方括号、圆括号、花括号）
  const allOpen = (trimmed.match(/[\[\(\{]/g) || []).length;
  const allClose = (trimmed.match(/[\]\)\}]/g) || []).length;
  if (allOpen !== allClose) return false;

  // 检查是否有不完整的行（流式截断）
  const lines = trimmed.split('\n');
  const lastLine = lines.pop().trim();

  // 检测不完整的箭头语法
  if (/--$/.test(lastLine)) return false; // 箭头 --> 被截断
  if (/==$/.test(lastLine)) return false; // 粗箭头 ==> 被截断
  if (/-\.$/.test(lastLine) || /-\.-$/.test(lastLine)) return false; // 虚线箭头 -.-> 被截断

  // 检测未闭合的标签（管道符）
  if (/\|[^|]*$/.test(lastLine)) {
    const pipeCount = (lastLine.match(/\|/g) || []).length;
    if (pipeCount % 2 !== 0) return false;
  }

  // 检测行内未闭合的括号
  for (const line of lines) {
    const lineOpen = (line.match(/[\[\(]/g) || []).length;
    const lineClose = (line.match(/[\]\)]/g) || []).length;
    if (lineOpen !== lineClose) return false;
  }

  // 检查是否以合理方式结尾
  const endsWithValidChar = /[\]})>;]$/.test(trimmed) ||
                            /\b(end)\s*$/.test(trimmed) ||
                            /(-->|---|==>)\s*\S+.*$/.test(lastLine);

  return hasOpen && (endsWithValidChar || code.split('\n').length > 3);
};

// 预处理 Mermaid 代码，修复常见语法错误
const preprocessMermaidCode = (code) => {
  if (!code) return '';

  let cleaned = code;

  // HTML 标签和实体清理
  cleaned = cleaned.replace(/<br\s*\/?>/gi, '\n');
  cleaned = cleaned.replace(/<\/?p[^>]*>/gi, '\n');
  cleaned = cleaned.replace(/<\/?div[^>]*>/gi, '\n');
  cleaned = cleaned.replace(/<\/?span[^>]*>/gi, '');
  cleaned = cleaned.replace(/&nbsp;/gi, ' ');
  cleaned = cleaned.replace(/&lt;/gi, '<');
  cleaned = cleaned.replace(/&gt;/gi, '>');
  cleaned = cleaned.replace(/&amp;/gi, '&');

  // 移除代码块标记（更严格的边界检测）
  cleaned = cleaned.replace(/^```(?:mermaid)?\s*[\r\n]?/i, '');
  cleaned = cleaned.replace(/[\r\n]?```\s*$/i, '');

  // 修复不完整的箭头（如 "A --> B -->" 后面没有目标）
  cleaned = cleaned.replace(/-->\s*$/gm, '');

  // 移除行首行尾空白，但保留缩进
  cleaned = cleaned.split('\n')
    .map(line => line.trimEnd())
    .join('\n');

  // 清理多余空行
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

  return cleaned.trim();
};

// 动态导入 mermaid 以支持异步加载（Promise 缓存模式，失败时可重试）
let mermaidInstance = null;
let initPromise = null;

const getMermaid = async () => {
  if (mermaidInstance) return mermaidInstance;

  if (!initPromise) {
    initPromise = (async () => {
      try {
        const mermaidModule = await import('mermaid');
        mermaidInstance = mermaidModule.default;
        await mermaidInstance.initialize({
          startOnLoad: false,
          theme: 'neutral',
          securityLevel: 'loose',
          fontFamily: 'inherit',
        });
        return mermaidInstance;
      } catch (err) {
        console.error('Mermaid 初始化失败:', err);
        initPromise = null; // 重置以便重试
        throw err;
      }
    })();
  }

  return initPromise;
};

// 全局计数器用于生成唯一 ID
let globalCounter = 0;

const MermaidRenderer = ({ code, onExpand, compact = false }) => {
  const [svgContent, setSvgContent] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [mermaid, setMermaid] = useState(null);
  const [idSuffix] = useState(() => ++idCounter);
  const [isFullscreen, setIsFullscreen] = useState(false);
  // 使用 ref 保存上一次成功渲染的 SVG，防止流式输出时闪烁回 loading 状态
  const lastSvgRef = useRef('');
  const lastRenderedCodeRef = useRef('');
  // 使用 ref 追踪失败状态，避免状态变化触发循环渲染
  const lastFailedCodeRef = useRef('');
  const failCountRef = useRef(0);
  const containerRef = useRef(null);

  // 初始化 mermaid
  useEffect(() => {
    const initMermaid = async () => {
      try {
        const instance = await getMermaid();
        setMermaid(instance);
        setIsLoading(false);
      } catch (err) {
        console.error('Mermaid 初始化失败:', err);
        setError('图表库加载失败');
        setIsLoading(false);
      }
    };

    initMermaid();
  }, []);

  // 渲染图表
  useEffect(() => {
    if (!code || isLoading || !mermaid) return;

    // 防抖：延迟渲染以避免流式输出期间频繁触发
    const timer = setTimeout(() => {
      // 使用自增计数器确保 ID 唯一
      const renderId = `mermaid-${idSuffix}-${Date.now()}-${globalCounter++}`;
      const cleanedCode = preprocessMermaidCode(code);

      // 检测代码是否完整（流式输出场景）
      const isComplete = isMermaidComplete(code);
      if (!isComplete) {
        console.debug('[Mermaid] 等待完整代码，当前长度:', code.length);
        return;
      }

      const renderDiagram = async () => {
        try {
          setError(null);
          // 不移除 setSvgContent('')，保留上一次有效的 SVG 内容，新 SVG 渲染完成后直接替换

          const { svg } = await mermaid.render(renderId, cleanedCode);
          setSvgContent(svg);
          // 保存成功渲染的 SVG 到 ref，用于防止流式输出时闪烁
          lastSvgRef.current = svg;
          lastRenderedCodeRef.current = code;
          // 渲染成功，重置失败状态
          lastFailedCodeRef.current = '';
          failCountRef.current = 0;
        } catch (err) {
          console.warn('[Mermaid] 渲染错误:', err);

          // 错误重试机制：代码变化时重置计数，连续失败且代码稳定后才显示错误
          if (code !== lastFailedCodeRef.current) {
            // 代码有变化，说明还在流式传输，重置计数
            lastFailedCodeRef.current = code;
            failCountRef.current = 1;
            // 不显示错误，保持 loading 状态
          } else {
            failCountRef.current += 1;
            if (failCountRef.current >= 2) {
              // 连续失败2次且代码没变化，显示错误
              let errorMsg = '图表渲染失败';
              if (err.message) {
                errorMsg = err.message.replace(/^Parse error on line \d+.*?\. /, '').substring(0, 100);
              }
              setError(errorMsg);
            }
          }
        }
      };

      renderDiagram();
    }, 300); // 300ms 防抖

    return () => clearTimeout(timer);
  }, [code, idSuffix, isLoading, mermaid, compact]);

  const containerStyle = {
    position: 'relative',
    background: '#f8fafc',
    borderRadius: '12px',
    padding: '16px',
    overflow: 'auto',
    // 固定高度防止流式输出时抖动（参考 deepseek 风格）
    minHeight: '200px',
    maxHeight: compact ? '350px' : '500px',
    height: '300px',
    width: '100%',
    boxSizing: 'border-box',
    contain: 'layout',
  };

  const svgWrapperStyle = {
    lineHeight: 0,
    width: '100%',
    height: '100%',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'flex-start',
    overflow: 'auto',
  };

  // 按钮组容器样式
  const btnGroupStyle = {
    position: 'absolute',
    top: '8px',
    right: '8px',
    display: 'flex',
    gap: '4px',
    zIndex: 2,
  };

  const btnStyle = {
    background: 'rgba(255,255,255,0.75)',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    padding: '4px 8px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    color: '#64748b',
    opacity: 0.7,
    transition: 'opacity 0.2s, background 0.2s',
  };

  // 全屏切换处理
  const handleFullscreen = useCallback(() => {
    if (!containerRef.current) return;

    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => {
        setIsFullscreen(true);
      }).catch(err => {
        console.error('全屏切换失败:', err);
      });
    } else {
      document.exitFullscreen().then(() => {
        setIsFullscreen(false);
      }).catch(err => {
        console.error('退出全屏失败:', err);
      });
    }
  }, []);

  // 监听 ESC 退出全屏
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // 下载 SVG 处理
  const handleDownload = useCallback(() => {
    const svgToDownload = svgContent || lastSvgRef.current;
    if (!svgToDownload) return;

    // 创建一个包含完整 SVG 的文档
    const svgDoc = `<!DOCTYPE html>
<html>
<head><title>Mermaid Chart</title></head>
<body style="margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#f8fafc;">
${svgToDownload}
</body>
</html>`;

    const blob = new Blob([svgDoc], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `mermaid-chart-${Date.now()}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [svgContent]);

  // 加载状态 - 如果有上一次成功渲染的 SVG，显示它而不是 loading
  if (isLoading) {
    if (lastSvgRef.current) {
      return (
        <div style={containerStyle} ref={containerRef}>
          <div
            dangerouslySetInnerHTML={{ __html: lastSvgRef.current }}
            style={svgWrapperStyle}
          />
          <div style={btnGroupStyle}>
            <button
              style={btnStyle}
              onClick={handleFullscreen}
              title={isFullscreen ? '退出全屏' : '全屏'}
            >
              {isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            </button>
            <button
              style={btnStyle}
              onClick={handleDownload}
              title="下载 SVG"
            >
              <DownloadOutlined />
            </button>
          </div>
        </div>
      );
    }
    return (
      <div style={containerStyle}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px',
          color: '#94a3b8',
        }}>
          <span style={{
            display: 'inline-block',
            width: 16,
            height: 16,
            border: '2px solid rgba(99,102,241,0.2)',
            borderTopColor: '#6366f1',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            marginRight: 8,
          }} />
          加载图表...
        </div>
      </div>
    );
  }

  if (error) {
    // 如果代码还在变化（流式传输中）且有上一次成功渲染的 SVG，显示上一次的 SVG
    const isStreaming = code !== lastRenderedCodeRef.current;
    if (isStreaming && lastSvgRef.current) {
      return (
        <div style={containerStyle} ref={containerRef}>
          <div
            dangerouslySetInnerHTML={{ __html: lastSvgRef.current }}
            style={svgWrapperStyle}
          />
          <div style={btnGroupStyle}>
            <button
              style={btnStyle}
              onClick={handleFullscreen}
              title={isFullscreen ? '退出全屏' : '全屏'}
            >
              {isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            </button>
            <button
              style={btnStyle}
              onClick={handleDownload}
              title="下载 SVG"
            >
              <DownloadOutlined />
            </button>
          </div>
        </div>
      );
    }
    return (
      <div style={containerStyle}>
        <div
          style={{
            background: '#fff3cd',
            border: '1px solid #ffc107',
            borderRadius: '8px',
            padding: '8px 12px',
            marginBottom: '8px',
            fontSize: '12px',
            color: '#856404',
          }}
        >
          ⚠️ 图表渲染失败: {error}
        </div>
        <pre
          style={{
            margin: 0,
            fontSize: '13px',
            color: '#475569',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}
        >
          {code}
        </pre>
      </div>
    );
  }

  return (
    <div style={containerStyle} ref={containerRef}>
      {svgContent && (
        <div
          dangerouslySetInnerHTML={{ __html: svgContent }}
          style={svgWrapperStyle}
        />
      )}
      <div style={btnGroupStyle}>
        <button
          style={btnStyle}
          onClick={handleFullscreen}
          title={isFullscreen ? '退出全屏' : '全屏'}
        >
          {isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
        </button>
        <button
          style={btnStyle}
          onClick={handleDownload}
          title="下载 SVG"
        >
          <DownloadOutlined />
        </button>
      </div>
    </div>
  );
};

export default MermaidRenderer;
