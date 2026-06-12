import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import SyntaxHighlighter, { oneDark, oneLight } from '../SyntaxHighlighter';
import { useHtmlSandbox } from './html/useHtmlSandbox';
import { useHtmlActions } from './html/useHtmlActions';
import HtmlActionBar from './html/HtmlActionBar';
import HtmlFullscreenModal from './html/HtmlFullscreenModal';
import { buildWsfilesUrl } from './html/wsfilesUrl';
import './HtmlViewer.css';

interface HtmlViewerProps {
  /** Full source (read unlimited so Source isn't truncated). */
  content: string;
  fileName: string;
  workspaceId: string;
  /** Path within the workspace, e.g. "results/report.html". */
  filePath: string;
  /** Download the server's original bytes for this file. */
  onTriggerDownload: () => void;
}

export default function HtmlViewer({
  content,
  fileName,
  workspaceId,
  filePath,
  onTriggerDownload,
}: HtmlViewerProps) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<'preview' | 'source'>('preview');
  const [fullscreen, setFullscreen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const { pushTheme } = useHtmlSandbox({ iframeRef, autoHeight: false });

  const servedUrl = useMemo(
    () => buildWsfilesUrl(workspaceId, filePath, { injectTheme: true }),
    [workspaceId, filePath],
  );

  const actions = useHtmlActions({
    mode: 'file',
    workspaceId,
    filePath,
    content,
    triggerDownload: () => Promise.resolve(onTriggerDownload()),
  });

  const isLight =
    typeof window !== 'undefined' &&
    document.documentElement.getAttribute('data-theme') === 'light';

  return (
    <div className="html-viewer">
      <div className="html-viewer-toolbar">
        <div className="html-viewer-tabs">
          <button
            className={`html-viewer-tab ${mode === 'preview' ? 'active' : ''}`}
            onClick={() => setMode('preview')}
          >
            {t('filePanel.htmlPreview')}
          </button>
          <button
            className={`html-viewer-tab ${mode === 'source' ? 'active' : ''}`}
            onClick={() => setMode('source')}
          >
            {t('filePanel.htmlSource')}
          </button>
        </div>
        <HtmlActionBar
          onFullscreen={() => setFullscreen(true)}
          onOpenInNewTab={actions.openInNewTab}
          onDownload={actions.downloadHtml}
          onExportPdf={actions.exportPdf}
          onCopySource={actions.copySource}
        />
      </div>
      {mode === 'preview' ? (
        <iframe
          ref={iframeRef}
          src={servedUrl}
          sandbox="allow-scripts"
          className="html-viewer-frame"
          title={fileName || 'HTML Preview'}
          onLoad={pushTheme}
        />
      ) : (
        <div className="html-viewer-source">
          <SyntaxHighlighter
            language="markup"
            style={isLight ? oneLight : oneDark}
            customStyle={{ margin: 0, padding: 0, backgroundColor: 'transparent', fontSize: '12px', lineHeight: '1.6' }}
            codeTagProps={{ style: { backgroundColor: 'transparent' } }}
            wrapLongLines
          >
            {content}
          </SyntaxHighlighter>
        </div>
      )}
      {fullscreen && (
        <HtmlFullscreenModal
          variant="file"
          open={fullscreen}
          onOpenChange={setFullscreen}
          title={fileName}
          workspaceId={workspaceId}
          filePath={filePath}
          actions={actions}
        />
      )}
    </div>
  );
}
