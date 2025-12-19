/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/

export interface Artifact {
  id: string;
  styleName: string;
  html: string;
  status: 'streaming' | 'complete' | 'error';
}

export interface Session {
    id: string;
    prompt: string;
    timestamp: number;
    artifacts: Artifact[];
}

export interface ChatMessage {
    role: 'user' | 'advisor' | 'system';
    text: string;
    timestamp: number;
}

export interface EnrolledProduct {
    id: string;
    name: string;
    value: string;
    status: string;
}

export interface Notification {
    id: string;
    title: string;
    message: string;
    type: 'approval' | 'info' | 'alert';
    read: boolean;
}

export interface ComponentVariation { name: string; html: string; }
export interface LayoutOption { name: string; css: string; previewHtml: string; }
