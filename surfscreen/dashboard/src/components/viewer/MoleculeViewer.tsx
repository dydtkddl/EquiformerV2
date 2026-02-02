'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Card } from '@/components/ui';
import { Skeleton } from '@/components/ui';
import { Button } from '@/components/ui';
import {
  RotateCw,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Palette,
  Box,
} from 'lucide-react';

// 3Dmol type declarations
declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    $3Dmol: any;
  }
}

type ViewerStyle = 'stick' | 'sphere' | 'cartoon' | 'surface';
type ColorScheme = 'element' | 'chain' | 'spectrum' | 'residue';

interface MoleculeViewerProps {
  /** Molecule data (CIF, XYZ, PDB, or SDF format) */
  data?: string;
  /** File format */
  format?: 'cif' | 'xyz' | 'pdb' | 'sdf';
  /** Initial style */
  style?: ViewerStyle;
  /** Background color */
  backgroundColor?: string;
  /** Height of the viewer */
  height?: number | string;
  /** Width of the viewer */
  width?: number | string;
  /** Show controls */
  showControls?: boolean;
  /** Additional className */
  className?: string;
  /** Loading state */
  isLoading?: boolean;
  /** Error message */
  error?: string;
  /** On load callback */
  onLoad?: () => void;
}

export function MoleculeViewer({
  data,
  format = 'xyz',
  style: initialStyle = 'stick',
  backgroundColor = '#1a1a2e',
  height = 400,
  width = '100%',
  showControls = true,
  className = '',
  isLoading = false,
  error,
  onLoad,
}: MoleculeViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<unknown>(null);
  const [is3DmolLoaded, setIs3DmolLoaded] = useState(false);
  const [currentStyle, setCurrentStyle] = useState<ViewerStyle>(initialStyle);
  const [colorScheme, setColorScheme] = useState<ColorScheme>('element');
  const [viewerError, setViewerError] = useState<string | null>(null);

  // Load 3Dmol.js dynamically
  useEffect(() => {
    if (typeof window !== 'undefined' && !window.$3Dmol) {
      const script = document.createElement('script');
      script.src = 'https://3Dmol.org/build/3Dmol-min.js';
      script.async = true;
      script.onload = () => {
        setIs3DmolLoaded(true);
      };
      script.onerror = () => {
        setViewerError('Failed to load 3Dmol.js library');
      };
      document.head.appendChild(script);
    } else if (window.$3Dmol) {
      setIs3DmolLoaded(true);
    }
  }, []);

  // Initialize viewer when 3Dmol is loaded and data is available
  useEffect(() => {
    if (!is3DmolLoaded || !containerRef.current || !data) return;

    try {
      const $3Dmol = window.$3Dmol;
      
      // Clear previous viewer
      if (viewerRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (viewerRef.current as any).clear();
      }

      // Create new viewer
      const viewer = $3Dmol.createViewer(containerRef.current, {
        backgroundColor,
        id: 'molecule-viewer',
      });

      viewerRef.current = viewer;

      // Add model
      viewer.addModel(data, format);
      
      // Apply initial style
      applyStyle(viewer, currentStyle, colorScheme);
      
      // Zoom to fit
      viewer.zoomTo();
      viewer.render();

      onLoad?.();
      setViewerError(null);
    } catch (err) {
      console.error('Failed to initialize 3Dmol viewer:', err);
      setViewerError('Failed to render molecule structure');
    }

    // Cleanup
    return () => {
      if (viewerRef.current) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (viewerRef.current as any).clear();
        viewerRef.current = null;
      }
    };
  }, [is3DmolLoaded, data, format, backgroundColor, onLoad]);

  // Update style when changed
  useEffect(() => {
    if (viewerRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      applyStyle(viewerRef.current as any, currentStyle, colorScheme);
    }
  }, [currentStyle, colorScheme]);

  const applyStyle = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (viewer: any, style: ViewerStyle, color: ColorScheme) => {
      viewer.setStyle({}, getStyleSpec(style, color));
      viewer.render();
    },
    []
  );

  const getStyleSpec = (style: ViewerStyle, color: ColorScheme) => {
    const colorSchemeSpec = getColorSchemeSpec(color);
    
    switch (style) {
      case 'stick':
        return { stick: { radius: 0.15, ...colorSchemeSpec } };
      case 'sphere':
        return { sphere: { scale: 0.3, ...colorSchemeSpec } };
      case 'cartoon':
        return { cartoon: { ...colorSchemeSpec } };
      case 'surface':
        return { surface: { opacity: 0.8, ...colorSchemeSpec } };
      default:
        return { stick: { radius: 0.15, ...colorSchemeSpec } };
    }
  };

  const getColorSchemeSpec = (scheme: ColorScheme) => {
    switch (scheme) {
      case 'element':
        return { colorscheme: 'Jmol' };
      case 'chain':
        return { colorscheme: 'chain' };
      case 'spectrum':
        return { colorscheme: 'spectral' };
      case 'residue':
        return { colorscheme: 'amino' };
      default:
        return { colorscheme: 'Jmol' };
    }
  };

  const handleZoomIn = () => {
    if (viewerRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (viewerRef.current as any).zoom(1.2, 300);
    }
  };

  const handleZoomOut = () => {
    if (viewerRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (viewerRef.current as any).zoom(0.8, 300);
    }
  };

  const handleReset = () => {
    if (viewerRef.current) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const viewer = viewerRef.current as any;
      viewer.zoomTo();
      viewer.render();
    }
  };

  const handleFullscreen = () => {
    if (containerRef.current) {
      containerRef.current.requestFullscreen?.();
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <Card className={className}>
        <div className="p-4">
          <Skeleton className="h-6 w-32 mb-4" />
          <Skeleton className="h-[400px] w-full" />
        </div>
      </Card>
    );
  }

  // Error state
  if (error || viewerError) {
    return (
      <Card className={className}>
        <div
          className="flex items-center justify-center bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400"
          style={{ height }}
        >
          <div className="text-center p-4">
            <Box className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="font-medium">Error Loading Molecule</p>
            <p className="text-sm mt-1">{error || viewerError}</p>
          </div>
        </div>
      </Card>
    );
  }

  // No data state
  if (!data) {
    return (
      <Card className={className}>
        <div
          className="flex items-center justify-center bg-gray-50 dark:bg-gray-800 text-gray-500"
          style={{ height }}
        >
          <div className="text-center p-4">
            <Box className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No molecule data provided</p>
            <p className="text-sm mt-1">Upload a CIF, XYZ, PDB, or SDF file</p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <div className="relative">
        {/* Viewer Container */}
        <div
          ref={containerRef}
          style={{
            height,
            width,
            position: 'relative',
          }}
          className="rounded-t-lg overflow-hidden"
        />

        {/* Controls */}
        {showControls && (
          <div className="absolute top-2 right-2 flex gap-1">
            <Button
              size="sm"
              variant="secondary"
              onClick={handleZoomIn}
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleZoomOut}
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleReset}
              title="Reset View"
            >
              <RotateCw className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleFullscreen}
              title="Fullscreen"
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
          </div>
        )}

        {/* Style/Color Controls */}
        {showControls && (
          <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 rounded-b-lg">
            <div className="flex flex-wrap gap-4">
              {/* Style Selector */}
              <div className="flex items-center gap-2">
                <Box className="w-4 h-4 text-gray-500" />
                <select
                  value={currentStyle}
                  onChange={(e) => setCurrentStyle(e.target.value as ViewerStyle)}
                  className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700"
                >
                  <option value="stick">Stick</option>
                  <option value="sphere">Sphere</option>
                  <option value="cartoon">Cartoon</option>
                  <option value="surface">Surface</option>
                </select>
              </div>

              {/* Color Selector */}
              <div className="flex items-center gap-2">
                <Palette className="w-4 h-4 text-gray-500" />
                <select
                  value={colorScheme}
                  onChange={(e) => setColorScheme(e.target.value as ColorScheme)}
                  className="text-sm border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-700"
                >
                  <option value="element">By Element</option>
                  <option value="chain">By Chain</option>
                  <option value="spectrum">Spectrum</option>
                  <option value="residue">By Residue</option>
                </select>
              </div>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

export default MoleculeViewer;
