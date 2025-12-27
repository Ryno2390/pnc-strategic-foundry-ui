
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/

import React from 'react';
import { Artifact } from '../types';

interface ArtifactCardProps {
    artifact: Artifact;
    isFocused: boolean;
    onClick: () => void;
}

const ArtifactCard = React.memo(({ 
    artifact, 
    isFocused, 
    onClick 
}: ArtifactCardProps) => {
    const isBlurring = artifact.status === 'streaming';

    return (
        <div 
            className={`artifact-card ${isFocused ? 'focused' : ''} ${isBlurring ? 'generating' : ''}`}
            onClick={!isFocused && !isBlurring ? onClick : undefined}
            style={{ cursor: !isFocused && !isBlurring ? 'pointer' : 'default' }}
        >
            <div className="artifact-header">
                <span className="artifact-style-tag">{artifact.styleName}</span>
                {!isFocused && (
                    <div className="artifact-expand-icon" style={{ fontSize: '0.7rem', color: 'var(--pnc-orange)', fontWeight: 800 }}>
                        EXECUTE STRATEGY ↗
                    </div>
                )}
            </div>
            <div className="artifact-card-inner">
                {isBlurring && (
                    <div className="generating-overlay">
                        <div className="analysis-loading-status">
                            <span className="loading-text">Synthesizing Strategic Intelligence...</span>
                            <div className="progress-bar-container">
                                <div className="progress-bar-fill"></div>
                            </div>
                        </div>
                    </div>
                )}
                
                {/* Transparent overlay captures clicks for expansion when not focused */}
                {!isFocused && !isBlurring && (
                    <div className="clickable-overlay" />
                )}

                <iframe 
                    srcDoc={artifact.html} 
                    title={artifact.id} 
                    sandbox="allow-scripts allow-forms allow-modals allow-popups allow-presentation allow-same-origin"
                    className="artifact-iframe"
                    scrolling={isFocused ? "yes" : "no"}
                    style={{ 
                        overflow: isFocused ? 'auto' : 'hidden',
                        pointerEvents: isFocused ? 'auto' : 'none'
                    }}
                />
            </div>
        </div>
    );
});

export default ArtifactCard;
