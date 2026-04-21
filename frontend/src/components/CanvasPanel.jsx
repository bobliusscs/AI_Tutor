import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CloseOutlined, CopyOutlined, DownloadOutlined, CheckOutlined } from '@ant-design/icons';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import MermaidRenderer from './MermaidRenderer';

// Type icon map
const TYPE_ICONS = {
  mermaid: '🔀',
  code: '💻',
  html: '🌐',
};

const CodeContent = ({ item }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(item.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
      const ta = document.createElement('textarea');
      ta.value = item.content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    const extMap = {
      javascript: 'js', js: 'js', typescript: 'ts', ts: 'ts',
      python: 'py', py: 'py', html: 'html', css: 'css',
      json: 'json', bash: 'sh', shell: 'sh', sql: 'sql',
    };
    const lang = (item.language || 'txt').toLowerCase();
    const ext = extMap[lang] || lang;
    const filename = `${item.title || 'code'}.${ext}`;
    const blob = new Blob([item.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const actionBarStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '6px 12px',
    background: '#1a1a2e',
    borderRadius: '8px 8px 0 0',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
  };

  const langTagStyle = {
    fontSize: '11px',
    fontWeight: 600,
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  };

  const btnStyle = {
    background: 'rgba(255,255,255,0.1)',
    border: '1px solid rgba(255,255,255,0.15)',
    borderRadius: '5px',
    padding: '3px 8px',
    cursor: 'pointer',
    color: '#94a3b8',
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    transition: 'background 0.2s, color 0.2s',
  };

  return (
    <div style={{ borderRadius: '8px', overflow: 'hidden', border: '1px solid #2d3748' }}>
      <div style={actionBarStyle}>
        <span style={langTagStyle}>{item.language || 'text'}</span>
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            style={btnStyle}
            onClick={handleCopy}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; e.currentTarget.style.color = '#e2e8f0'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; e.currentTarget.style.color = '#94a3b8'; }}
          >
            {copied ? <CheckOutlined style={{ color: '#10b981' }} /> : <CopyOutlined />}
            {copied ? '已复制' : '复制'}
          </button>
          <button
            style={btnStyle}
            onClick={handleDownload}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; e.currentTarget.style.color = '#e2e8f0'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; e.currentTarget.style.color = '#94a3b8'; }}
          >
            <DownloadOutlined />
            下载
          </button>
        </div>
      </div>
      <SyntaxHighlighter
        language={item.language || 'text'}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: '0 0 8px 8px',
          fontSize: '13px',
          lineHeight: '1.6',
          maxHeight: 'none',
        }}
        showLineNumbers
      >
        {item.content}
      </SyntaxHighlighter>
    </div>
  );
};

const HtmlContent = ({ item }) => (
  <div style={{ borderRadius: '8px', overflow: 'hidden', border: '1px solid #e2e8f0', height: '480px' }}>
    <iframe
      srcDoc={item.content}
      title={item.title || 'HTML预览'}
      style={{ width: '100%', height: '100%', border: 'none' }}
      sandbox="allow-scripts allow-same-origin"
    />
  </div>
);

const CanvasPanel = ({ visible, onClose, items = [], activeIndex = 0, onTabChange }) => {
  const activeItem = items[activeIndex] || null;

  const panelStyle = {
    position: 'fixed',
    top: 0,
    right: 0,
    width: '480px',
    height: '100%',
    background: '#ffffff',
    borderLeft: '1px solid #e2e8f0',
    boxShadow: '-4px 0 24px rgba(0,0,0,0.08)',
    zIndex: 100,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  };

  const headerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 16px',
    background: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    flexShrink: 0,
  };

  const closeBtnStyle = {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    padding: '6px',
    borderRadius: '6px',
    color: '#64748b',
    fontSize: '15px',
    display: 'flex',
    alignItems: 'center',
    transition: 'background 0.15s, color 0.15s',
  };

  const titleStyle = {
    fontSize: '14px',
    fontWeight: 600,
    color: '#1e293b',
    flex: 1,
    textAlign: 'right',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    paddingLeft: '8px',
  };

  const tabBarStyle = {
    display: 'flex',
    overflowX: 'auto',
    borderBottom: '1px solid #e2e8f0',
    background: '#f8fafc',
    flexShrink: 0,
    scrollbarWidth: 'none',
  };

  const tabStyle = (isActive) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    padding: '8px 14px',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    fontSize: '13px',
    fontWeight: isActive ? 600 : 400,
    color: isActive ? '#1e293b' : '#94a3b8',
    borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
    background: 'none',
    border: 'none',
    borderBottomColor: isActive ? '#3b82f6' : 'transparent',
    borderBottomWidth: '2px',
    borderBottomStyle: 'solid',
    transition: 'color 0.15s',
    flexShrink: 0,
  });

  const contentStyle = {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
  };

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          style={panelStyle}
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
        >
          {/* Header */}
          <div style={headerStyle}>
            <button
              style={closeBtnStyle}
              onClick={onClose}
              onMouseEnter={e => { e.currentTarget.style.background = '#f1f5f9'; e.currentTarget.style.color = '#1e293b'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = '#64748b'; }}
              title="关闭"
            >
              <CloseOutlined />
            </button>
            <span style={titleStyle}>
              {activeItem ? activeItem.title : '画布'}
            </span>
          </div>

          {/* Tab bar – only show when multiple items */}
          {items.length > 1 && (
            <div style={tabBarStyle}>
              {items.map((item, idx) => (
                <button
                  key={item.id || idx}
                  style={tabStyle(idx === activeIndex)}
                  onClick={() => onTabChange && onTabChange(idx)}
                >
                  <span>{TYPE_ICONS[item.type] || '📄'}</span>
                  <span>{item.title}</span>
                </button>
              ))}
            </div>
          )}

          {/* Content area */}
          <div style={contentStyle}>
            {activeItem ? (
              <>
                {activeItem.type === 'mermaid' && (
                  <MermaidRenderer code={activeItem.content} compact={false} />
                )}
                {activeItem.type === 'code' && (
                  <CodeContent item={activeItem} />
                )}
                {activeItem.type === 'html' && (
                  <HtmlContent item={activeItem} />
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', color: '#94a3b8', marginTop: '60px', fontSize: '14px' }}>
                暂无内容
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default CanvasPanel;
