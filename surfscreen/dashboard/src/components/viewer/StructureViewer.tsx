'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui';
import { RotateCcw, Camera, Maximize } from 'lucide-react';

interface StructureViewerProps {
  xyzData?: string;
  height?: number;
  className?: string;
}

// Note: 3Dmol.js는 CDN에서 로드
declare global {
  interface Window {
    $3Dmol: any;
  }
}

export function StructureViewer({ xyzData, height = 400, className }: StructureViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const [loaded, setLoaded] = useState(false);
  const [style, setStyle] = useState<'sphere' | 'stick' | 'ball'>('stick');

  // 3Dmol.js 스크립트 로드
  useEffect(() => {
    if (typeof window !== 'undefined' && !window.$3Dmol) {
      const script = document.createElement('script');
      script.src = 'https://3Dmol.org/build/3Dmol-min.js';
      script.async = true;
      script.onload = () => setLoaded(true);
      document.head.appendChild(script);
    } else if (window.$3Dmol) {
      setLoaded(true);
    }
  }, []);

  // Viewer 초기화
  useEffect(() => {
    if (!loaded || !containerRef.current || !xyzData) return;

    const element = containerRef.current;
    element.innerHTML = '';
    
    const config = { backgroundColor: '#0f172a' };
    const viewer = window.$3Dmol.createViewer(element, config);
    
    viewer.addModel(xyzData, 'xyz');
    applyStyle(viewer, style);
    viewer.zoomTo();
    viewer.render();
    
    viewerRef.current = viewer;

    return () => {
      if (viewerRef.current) {
        viewerRef.current.clear();
      }
    };
  }, [loaded, xyzData]);

  // 스타일 변경
  useEffect(() => {
    if (viewerRef.current) {
      applyStyle(viewerRef.current, style);
      viewerRef.current.render();
    }
  }, [style]);

  const applyStyle = (viewer: any, styleType: string) => {
    viewer.setStyle({}, {});
    switch (styleType) {
      case 'sphere':
        viewer.setStyle({}, { sphere: { colorscheme: 'Jmol', scale: 0.25 } });
        break;
      case 'ball':
        viewer.setStyle({}, { sphere: { colorscheme: 'Jmol', scale: 0.5 } });
        viewer.setStyle({}, { stick: { colorscheme: 'Jmol', radius: 0.1 } });
        break;
      case 'stick':
      default:
        viewer.setStyle({}, { stick: { colorscheme: 'Jmol', radius: 0.15 } });
        break;
    }
  };

  const handleReset = () => {
    if (viewerRef.current) {
      viewerRef.current.zoomTo();
      viewerRef.current.render();
    }
  };

  const handleScreenshot = () => {
    if (viewerRef.current) {
      const dataUrl = viewerRef.current.pngURI();
      const link = document.createElement('a');
      link.href = dataUrl;
      link.download = 'structure.png';
      link.click();
    }
  };

  return (
    <div className={className}>
      {/* 컨트롤 */}
      <div className="flex items-center gap-2 mb-2">
        <div className="flex gap-1 bg-gray-200 dark:bg-gray-700 rounded-lg p-1">
          {(['stick', 'sphere', 'ball'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setStyle(s)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                style === s
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-300 dark:hover:bg-gray-600'
              }`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <Button variant="ghost" size="sm" onClick={handleReset} title="Reset view">
          <RotateCcw className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="sm" onClick={handleScreenshot} title="Screenshot">
          <Camera className="w-4 h-4" />
        </Button>
      </div>

      {/* Viewer */}
      <div
        ref={containerRef}
        style={{ height }}
        className="w-full rounded-lg bg-gray-900 overflow-hidden"
      >
        {!xyzData && (
          <div className="flex items-center justify-center h-full text-gray-500">
            No structure data
          </div>
        )}
      </div>
    </div>
  );
}
