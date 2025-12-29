
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/

import { GoogleGenAI } from '@google/genai';
import React, { useState, useCallback, useEffect, useRef } from 'react';
import ReactDOM from 'react-dom/client';

import { Artifact, Session, ChatMessage, Notification, EnrolledProduct } from './types';
import { INITIAL_PLACEHOLDERS } from './constants';
import { generateId } from './utils';

import DottedGlowBackground from './components/DottedGlowBackground';
import ArtifactCard from './components/ArtifactCard';
import SideDrawer from './components/SideDrawer';
import RelationshipGraph from './components/RelationshipGraph';
import { 
    ThinkingIcon, 
    UserIcon,
    ArrowUpIcon, 
    GridIcon,
    HomeIcon,
    ArrowLeftIcon,
    ArrowRightIcon,
    NetworkIcon
} from './components/Icons';

// New Icons for Enhanced Chat
const MaximizeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
);
const MinimizeIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7"/></svg>
);
const PaperclipIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
);

const SYSTEM_INSTRUCTION = `
You are the "Student" model of the PNC Strategic Foundry. Your purpose is to act as a Strategic AI Advisor for Middle Market CEOs. 
You leverage a simulated "Global Map" to provide non-obvious insights and seamless product upsells.

REQUIRED RESPONSE STRUCTURE:
1. Executive Summary: 2-sentence "Bottom Line Up Front."
2. The Global Map View: Client vs sector comparison.
3. Actionable Strategy: Step-by-step guidance.
4. Foundry Solution: A specific PNC product recommendation.

**UNIQUENESS RULE:**
You are generating one of three unique analysis cards. Ensure your content is distinct from the others (e.g., focus strictly on one of: Liquidity, Supply Chain, or Market Benchmarks).

**ACTIONABILITY RULE:**
Every Foundry Solution section MUST include a large button styled with PNC Orange (#EF6A00). 
Crucially, the button must trigger a message to the parent window when clicked.
Example HTML: 
<button onclick="window.parent.postMessage({type: 'ADVISOR_INIT', product: 'Treasury Management', initialMessage: 'I am interested in automating my treasury workflows. How do we start?'}, '*')" style="background:#EF6A00; color:white; padding:15px 25px; border:none; font-weight:bold; cursor:pointer; width:100%;">Activate Treasury Sweep</button>

VISUAL GUIDELINES:
- Palette: #EF6A00 (Orange), #333F48 (Dark Grey), #EDEDEE (Light Gray).
- Style: "Brilliantly Boring" - focus on clarity and high trust.
- Layout: EDGE-TO-EDGE DASHBOARD. No large white margins.
`;

function App() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionIndex, setCurrentSessionIndex] = useState<number>(-1);
  const [focusedArtifactIndex, setFocusedArtifactIndex] = useState<number | null>(null);
  const [isGraphOpen, setIsGraphOpen] = useState(false);
  
  const [inputValue, setInputValue] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [placeholders] = useState<string[]>(INITIAL_PLACEHOLDERS);
  const [isAutoCycling, setIsAutoCycling] = useState(true);
  
  // Profile, Stats & Notifications
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [enrolledProducts, setEnrolledProducts] = useState<EnrolledProduct[]>([]);
  const [selectedStatDetail, setSelectedStatDetail] = useState<{name: string, value: string} | null>(null);
  const [isStatModalOpen, setIsStatModalOpen] = useState(false);
  const [statDetailHtml, setStatDetailHtml] = useState<string>('');
  const [isStatDetailLoading, setIsStatDetailLoading] = useState(false);

  const [notifications, setNotifications] = useState<Notification[]>([
      { id: '1', title: 'Foundry Provisioned', message: 'Your Strategic advisor is active and analyzing RID-1189628825.', type: 'info', read: false },
      { id: '2', title: 'Trace Detected', message: 'Non-obvious correlation found in regional Q3 cash flow traces.', type: 'alert', read: false }
  ]);
  const [selectedNotif, setSelectedNotif] = useState<Notification | null>(null);
  const [isNotifModalOpen, setIsNotifModalOpen] = useState(false);
  const [notifDetailHtml, setNotifDetailHtml] = useState<string>('');
  const [isNotifDetailLoading, setIsNotifDetailLoading] = useState(false);

  // Advisor Chat
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isChatExpanded, setIsChatExpanded] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isChatLoading]);

  // Listen for actions from inside the iframes AND the local modal
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
        if (event.data.type === 'ADVISOR_INIT') {
            const { product, initialMessage } = event.data;
            // Close any open modals/drawers when starting a conversation
            setIsStatModalOpen(false);
            setIsNotifModalOpen(false);
            setIsProfileOpen(false);
            initiateAdvisorChat(product, initialMessage);
        }
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [enrolledProducts]); // Refresh listener when products change to capture latest state

  const initiateAdvisorChat = async (product: string, initialMessage: string) => {
      setIsChatOpen(true);
      const userMsg: ChatMessage = { role: 'user', text: initialMessage, timestamp: Date.now() };
      setChatMessages([userMsg]);
      setIsChatLoading(true);

      // Check if user is already enrolled in this product category
      const isAlreadyEnrolled = enrolledProducts.some(p => 
        product.toLowerCase().includes(p.name.toLowerCase()) || 
        p.name.toLowerCase().includes(product.toLowerCase())
      );

      setTimeout(async () => {
          const apiKey = process.env.API_KEY;
          if (!apiKey) return;
          const ai = new GoogleGenAI({ apiKey });
          
          const enrollmentContext = isAlreadyEnrolled 
            ? "The user is ALREADY ENROLLED in this strategic service. Your tone should be technical and optimization-focused."
            : "The user is NOT yet enrolled. Focus on the strategic 'Why'.";

          const response = await ai.models.generateContent({
              model: 'gemini-3-flash-preview',
              contents: [{ role: 'user', parts: [{ text: `A user (RID-1189628825) is inquiring about: ${product}. Initial prompt: ${initialMessage}. Context: ${enrollmentContext}` }] }],
              config: { 
                systemInstruction: "You are Sarah V., an elite Strategic Advisor at the PNC Strategic Foundry. Be brief, insightful, and professional. USE PLAIN TEXT ONLY. DO NOT USE MARKDOWN (No asterisks like **, no hashtags like ##, and no bullet points using asterisks). Write like a human professional sending a direct message." 
              }
          });

          const advisorMsg: ChatMessage = { role: 'advisor', text: response.text || "I've reviewed your current traces. Let's discuss how to optimize this strategy.", timestamp: Date.now() };
          setChatMessages(prev => [...prev, advisorMsg]);
          setIsChatLoading(false);

          // Approval Simulation for new enrollments
          if (!isAlreadyEnrolled) {
              setTimeout(() => {
                  const approvalNotif: Notification = {
                      id: generateId(),
                      title: 'Strategy Enrolled',
                      message: `Your ${product} setup has been approved by our HITL review team. Check the Executive Portal for active traces.`,
                      type: 'approval',
                      read: false
                  };
                  setNotifications(prev => [approvalNotif, ...prev]);
                  
                  setEnrolledProducts(prev => {
                      if (prev.find(p => p.name === product)) return prev;
                      return [...prev, {
                          id: generateId(),
                          name: product,
                          value: 'Active',
                          status: 'Approved'
                      }];
                  });
              }, 12000);
          }
      }, 1500);
  };

  const handleStatClick = async (statName: string, statValue: string) => {
      setSelectedStatDetail({ name: statName, value: statValue });
      setIsStatModalOpen(true);
      setIsStatDetailLoading(true);
      setStatDetailHtml('');

      try {
          const isEnrolled = enrolledProducts.some(p => p.name === statName);
          const apiKey = process.env.API_KEY;
          const ai = new GoogleGenAI({ apiKey: apiKey! });
          
          const detailSystemInstruction = `You are the "Student" model of the PNC Strategic Foundry.
Role: Strategic AI Advisor for Middle Market CEOs.
Tone: Professional, Direct, High-Intelligence, "Brilliantly Boring".
Formatting Rules:
1. Output highly structured HTML fragments.
2. Wrap major sections in <section> tags.
3. Use <h3> for primary headers and <h4> for sub-headers.
4. Include at least one <table> for data comparisons/benchmarks.
5. NO EMOJIS.
6. Use clear, industrial-grade business terminology.
7. Wrap the Executive Summary in a div with class "executive-summary".

Structure:
- Section 1: Executive Summary
- Section 2: Global Map Comparison (with Table)
- Section 3: Actionable Strategy (3 key steps in a list)
- Section 4: Foundry Solution (Specific recommendation with Action Button)`;

          const prompt = `Perform a deep-trace strategic analysis for "${statName}" at current level: $${statValue}.
Customer: RID-1189628825. Status: ${isEnrolled ? 'Active Enrolled' : 'Prospective'}.
Map this against the Global Map sector benchmarks.

The report MUST end with this Foundry Solution button:
<button onclick="window.postMessage({type: 'ADVISOR_INIT', product: '${statName}', initialMessage: 'Initiate ${statName} optimization for RID-1189628825.' }, '*')" class="foundry-action-btn">${isEnrolled ? 'RE-OPTIMIZE STRATEGIC TRACE' : 'EXECUTE FOUNDRY STRATEGY'}</button>`;

          const response = await ai.models.generateContent({
              model: 'gemini-3-flash-preview',
              contents: [{ role: 'user', parts: [{ text: prompt }] }],
              config: { systemInstruction: detailSystemInstruction }
          });
          // Robust HTML extraction
          const cleanHtml = (response.text || '').trim().replace(/^```html\n?|```$/g, '');
          setStatDetailHtml(cleanHtml);
      } catch (e) {
          setStatDetailHtml('<p>Failed to load strategic intelligence. Please retry.</p>');
      } finally {
          setIsStatDetailLoading(false);
      }
  };

  const handleNotificationClick = async (notif: Notification) => {
      // Mark as read immediately
      setNotifications(prev => prev.map(n => n.id === notif.id ? {...n, read: true} : n));
      
      setSelectedNotif(notif);
      setIsNotifModalOpen(true);
      setIsNotifDetailLoading(true);
      setNotifDetailHtml('');

      try {
          const apiKey = process.env.API_KEY;
          const ai = new GoogleGenAI({ apiKey: apiKey! });
          
          const traceSystemInstruction = `You are the "Student" model of the PNC Strategic Foundry. 
Your specialty is Bayesian Trace Analysis—identifying hidden risks and opportunities from billions of market data points.

Generate a Strategic Trace Detail Report for the following alert:
Title: "${notif.title}"
Context: "${notif.message}"

Structure:
- Section 1: Bayesian Prior Update (Explain the shifting market context).
- Section 2: The Global Map Correlation (Include a table comparing the user's specific traces against sector averages).
- Section 3: Mitigation or Optimization Roadmap (3-step action plan).
- Section 4: Foundry Strategic Execution (Action button).

Tone: High-intelligence, industrial-grade advisor. NO EMOJIS.
Format: HTML fragments only. Use <section>, <h3>, <h4>, <table>, <p>.`;

          const prompt = `Generate a deep-trace intelligence report for RID-1189628825 regarding the alert: ${notif.title}.
Include a Foundry Solution button at the end with this exact HTML structure:
<button onclick="window.postMessage({type: 'ADVISOR_INIT', product: 'Trace Execution: ${notif.title}', initialMessage: 'I am responding to the ${notif.title} trace alert. What are the next steps for mitigation and capture?' }, '*')" class="foundry-action-btn">EXECUTE TRACE MITIGATION</button>`;

          const response = await ai.models.generateContent({
              model: 'gemini-3-flash-preview',
              contents: [{ role: 'user', parts: [{ text: prompt }] }],
              config: { systemInstruction: traceSystemInstruction }
          });
          
          const cleanHtml = (response.text || '').trim().replace(/^```html\n?|```$/g, '');
          setNotifDetailHtml(cleanHtml);
      } catch (e) {
          setNotifDetailHtml('<p>Trace analysis failed to synthesize. Please re-query Sarah V. via the Advisor chat.</p>');
      } finally {
          setIsNotifDetailLoading(false);
      }
  };

  const handleSendChatMessage = async () => {
      if (!chatInput.trim() || isChatLoading) return;
      const text = chatInput;
      setChatInput('');
      setChatMessages(prev => [...prev, { role: 'user', text, timestamp: Date.now() }]);
      setIsChatLoading(true);

      const apiKey = process.env.API_KEY;
      if (!apiKey) return;
      const ai = new GoogleGenAI({ apiKey });

      const enrolledStr = enrolledProducts.map(p => p.name).join(", ");
      const response = await ai.models.generateContent({
          model: 'gemini-3-flash-preview',
          contents: [{ role: 'user', parts: [{ text }] }],
          config: { 
            systemInstruction: `You are Sarah V., Strategic Advisor. User RID-1189628825. Active Products: [${enrolledStr}]. Be direct and professional. USE PLAIN TEXT ONLY. DO NOT USE MARKDOWN (NO **, ##, OR LISTS WITH ASTERISKS). Format as a natural human conversation in a chat window.` 
          }
      });

      setChatMessages(prev => [...prev, { role: 'advisor', text: response.text || '', timestamp: Date.now() }]);
      setIsChatLoading(false);
  };

  const handleAttachClick = () => {
      fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      
      const fileMsg: ChatMessage = { 
          role: 'system', 
          text: `📎 Document Attached: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`, 
          timestamp: Date.now() 
      };
      setChatMessages(prev => [...prev, fileMsg]);
      
      setIsChatLoading(true);
      setTimeout(() => {
          const analyzerMsg: ChatMessage = { 
              role: 'advisor', 
              text: `I've ingested your ${file.name}. My preliminary analysis shows a 14% correlation with your Q3 retail spend traces. Would you like me to map this data against the Global Map industry averages?`, 
              timestamp: Date.now() 
          };
          setChatMessages(prev => [...prev, analyzerMsg]);
          setIsChatLoading(false);
      }, 2500);
  };

  useEffect(() => {
      if (!isAutoCycling) return;
      const interval = setInterval(() => {
          setPlaceholderIndex(prev => (prev + 1) % placeholders.length);
      }, 4000);
      return () => clearInterval(interval);
  }, [placeholders.length, isAutoCycling]);

  const handleSendMessage = useCallback(async (manualPrompt?: string) => {
    const promptToUse = manualPrompt || (inputValue.trim() || placeholders[placeholderIndex]);
    const trimmedInput = promptToUse.trim();
    if (!trimmedInput || isLoading) return;
    setInputValue('');
    setIsLoading(true);

    const sessionId = generateId();
    const placeholderArtifacts: Artifact[] = Array(3).fill(null).map((_, i) => ({
        id: `${sessionId}_${i}`,
        styleName: 'Synthesizing...',
        html: '',
        status: 'streaming',
    }));

    setSessions(prev => [...prev, { id: sessionId, prompt: trimmedInput, timestamp: Date.now(), artifacts: placeholderArtifacts }]);
    setCurrentSessionIndex(sessions?.length || 0); 
    setFocusedArtifactIndex(null); 

    try {
        const apiKey = process.env.API_KEY;
        const ai = new GoogleGenAI({ apiKey: apiKey! });

        const stylePrompt = `For: "${trimmedInput}", identify 3 UNIQUE and DISTINCT analysis vectors. Return JSON array of 3 labels.`;

        const styleResponse = await ai.models.generateContent({
            model: 'gemini-3-flash-preview',
            contents: { role: 'user', parts: [{ text: stylePrompt }] }
        });

        let generatedStyles: string[] = ["Liquidity Analysis", "Operational Trace", "Market Benchmarks"];
        try {
            const parsed = JSON.parse(styleResponse.text || '[]');
            if (Array.isArray(parsed) && parsed.length >= 3) generatedStyles = parsed.slice(0, 3);
        } catch (e) {}

        setSessions(prev => prev.map(s => s.id === sessionId ? {
            ...s, artifacts: s.artifacts.map((art, i) => ({ ...art, styleName: generatedStyles[i] }))
        } : s));

        const generateArtifact = async (artifact: Artifact, styleName: string) => {
            const response = await ai.models.generateContent({
                model: 'gemini-3-flash-preview',
                contents: [{ parts: [{ text: `Generate a dashboard card for ${styleName} based on prompt: "${trimmedInput}".` }], role: "user" }],
                config: { systemInstruction: SYSTEM_INSTRUCTION }
            });
            
            let finalHtml = (response.text || '').trim().replace(/^```html\n?|```$/g, '');
            setSessions(current => (current || []).map(sess => 
                sess.id === sessionId ? {
                    ...sess,
                    artifacts: sess.artifacts.map(art => 
                        art.id === artifact.id ? { ...art, html: finalHtml, status: 'complete' } : art
                    )
                } : sess
            ));
        };

        await Promise.all(placeholderArtifacts.map((art, i) => generateArtifact(art, generatedStyles[i])));
    } catch (err) {
        console.error("Strategic synthesis failed:", err);
    } finally {
        setIsLoading(false);
    }
  }, [inputValue, isLoading, sessions, placeholders, placeholderIndex]);

  const goHome = () => {
      setCurrentSessionIndex(-1);
      setFocusedArtifactIndex(null);
      setInputValue('');
  };

  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowUp') {
        e.preventDefault();
        setPlaceholderIndex(prev => (prev - 1 + placeholders.length) % placeholders.length);
        setIsAutoCycling(false);
    } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setPlaceholderIndex(prev => (prev + 1) % placeholders.length);
        setIsAutoCycling(false);
    } else if (e.key === 'Enter') {
        handleSendMessage();
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <>
        <div className="top-actions-bar">
            <div className="profile-portal-trigger" onClick={() => setIsProfileOpen(true)}>
                <UserIcon />
                {unreadCount > 0 && <div className="notification-badge">{unreadCount}</div>}
            </div>
            <div className="graph-explorer-trigger" onClick={() => setIsGraphOpen(true)} title="Relationship Explorer">
                <NetworkIcon />
            </div>
        </div>

        {/* Relationship Explorer Modal */}
        {isGraphOpen && (
            <div className="detail-modal-overlay" onClick={() => setIsGraphOpen(false)}>
                <div className="detail-modal-content graph-modal" onClick={e => e.stopPropagation()}>
                    <div className="detail-modal-header">
                        <div className="header-group">
                            <span className="artifact-style-tag">Enterprise Intelligence</span>
                            <h2>Unified Relationship Explorer</h2>
                        </div>
                        <button className="close-button" onClick={() => setIsGraphOpen(false)}>&times;</button>
                    </div>
                    <div className="detail-modal-body" style={{ height: '70vh' }}>
                        <RelationshipGraph />
                    </div>
                    <div className="detail-modal-footer">
                        <button className="pnc-action-btn" onClick={() => setIsGraphOpen(false)}>Return to Dashboard</button>
                    </div>
                </div>
            </div>
        )}

        {/* Executive Portal Side Drawer */}
        <SideDrawer isOpen={isProfileOpen} onClose={() => setIsProfileOpen(false)} title="Executive Portal">
            <div className="profile-header">
                <h3 style={{margin: 0, fontSize: '1.1rem'}}>RID-1189628825</h3>
                <p style={{margin: 0, opacity: 0.7, fontSize: '0.85rem'}}>Middle Market: Global Industrial Group</p>
            </div>
            
            <div className="profile-stats-grid">
                {[
                    {name: 'Liquidity Access', value: '$24.5M'},
                    {name: 'Avg Yield', value: '4.1%'},
                    {name: 'Risk Rating', value: 'AAA'},
                    {name: 'Merchant Vol', value: '$1.2M'},
                    ...enrolledProducts.map(p => ({name: p.name, value: p.value}))
                ].map((stat, idx) => (
                    <div 
                        key={`${stat.name}-${idx}`} 
                        className="stat-card clickable" 
                        onClick={() => handleStatClick(stat.name, stat.value)}
                    >
                        <div className="stat-label">{stat.name}</div>
                        <div className="stat-value">{stat.value}</div>
                        <div className="stat-hint">Consult Strategy ↗</div>
                    </div>
                ))}
            </div>

            <div className="notification-list">
                <div className="artifact-style-tag" style={{marginBottom: '10px', color: 'var(--pnc-orange)'}}>Message Center</div>
                {notifications.length === 0 ? <p style={{fontSize: '0.8rem', opacity: 0.5}}>No new messages</p> : 
                    notifications.map(notif => (
                        <div 
                            key={notif.id} 
                            className={`notif-item ${notif.read ? 'read' : ''}`} 
                            onClick={() => handleNotificationClick(notif)}
                        >
                            <span className="notif-title">{notif.title}</span>
                            <span className="notif-msg">{notif.message}</span>
                            <span className="stat-hint" style={{ fontSize: '0.65rem', marginTop: '4px' }}>Analyze Trace ↗</span>
                        </div>
                    ))
                }
            </div>
        </SideDrawer>

        {/* Granular Detail Modal (Reused for Stats and Notifications) */}
        {isStatModalOpen && (
            <div className="detail-modal-overlay" onClick={() => setIsStatModalOpen(false)}>
                <div className="detail-modal-content" onClick={e => e.stopPropagation()}>
                    <div className="detail-modal-header">
                        <div className="header-group">
                            <span className="artifact-style-tag">Strategic Intelligence breakdown</span>
                            <h2>{selectedStatDetail?.name}</h2>
                        </div>
                        <button className="close-button" onClick={() => setIsStatModalOpen(false)}>&times;</button>
                    </div>
                    <div className="detail-modal-body">
                        {isStatDetailLoading ? (
                            <div className="modal-loading">
                                <ThinkingIcon />
                                <span>Querying Global Map for Granular Details...</span>
                            </div>
                        ) : (
                            <div className="dynamic-modal-html-container" dangerouslySetInnerHTML={{ __html: statDetailHtml }} />
                        )}
                    </div>
                    <div className="detail-modal-footer">
                        <button className="pnc-action-btn secondary" onClick={() => setIsStatModalOpen(false)}>Close Strategic Report</button>
                    </div>
                </div>
            </div>
        )}

        {/* Trace Intelligence Modal */}
        {isNotifModalOpen && (
            <div className="detail-modal-overlay" onClick={() => setIsNotifModalOpen(false)}>
                <div className="detail-modal-content" onClick={e => e.stopPropagation()}>
                    <div className="detail-modal-header">
                        <div className="header-group">
                            <span className="artifact-style-tag">Bayesian Trace Analysis</span>
                            <h2>{selectedNotif?.title}</h2>
                        </div>
                        <button className="close-button" onClick={() => setIsNotifModalOpen(false)}>&times;</button>
                    </div>
                    <div className="detail-modal-body">
                        {isNotifDetailLoading ? (
                            <div className="modal-loading">
                                <ThinkingIcon />
                                <span>Correlating Market Factors & Bayesian Priors...</span>
                            </div>
                        ) : (
                            <div className="dynamic-modal-html-container" dangerouslySetInnerHTML={{ __html: notifDetailHtml }} />
                        )}
                    </div>
                    <div className="detail-modal-footer">
                        <button className="pnc-action-btn secondary" onClick={() => setIsNotifModalOpen(false)}>Dismiss Intelligence</button>
                    </div>
                </div>
            </div>
        )}

        <div className={`advisor-chat-widget ${isChatOpen ? '' : 'minimized'} ${isChatExpanded ? 'expanded' : ''}`}>
            {isChatExpanded && <div className="chat-expanded-overlay" onClick={() => setIsChatExpanded(false)} />}
            <div className="advisor-chat-container">
                <div className="chat-header">
                    <div className="chat-header-info" onClick={() => setIsChatOpen(!isChatOpen)}>
                        <h3>Advisor: Sarah V.</h3>
                        <span>{isChatOpen ? '−' : '+'}</span>
                    </div>
                    {isChatOpen && (
                        <button className="chat-expand-btn" onClick={() => setIsChatExpanded(!isChatExpanded)}>
                            {isChatExpanded ? <MinimizeIcon /> : <MaximizeIcon />}
                        </button>
                    )}
                </div>
                {isChatOpen && (
                    <>
                        <div className="chat-body">
                            {chatMessages.length === 0 && <div className="message advisor" style={{ whiteSpace: 'pre-wrap' }}>Welcome, RID-1189628825. I am Sarah V., your Strategic Foundry Advisor. How shall we execute today?</div>}
                            {chatMessages.map((msg, i) => (
                                <div key={i} className={`message ${msg.role}`} style={{ whiteSpace: 'pre-wrap' }}>
                                    {msg.text.replace(/\*\*/g, '').replace(/###/g, '').replace(/##/g, '').replace(/#/g, '')}
                                </div>
                            ))}
                            {isChatLoading && <div className="message advisor"><ThinkingIcon /> Accessing Global Map traces...</div>}
                            <div ref={chatEndRef} />
                        </div>
                        <div className="chat-input-area">
                            <input 
                                type="file" 
                                ref={fileInputRef} 
                                style={{ display: 'none' }} 
                                onChange={handleFileChange} 
                                accept=".pdf,.xlsx,.csv,.txt" 
                            />
                            <button className="attach-button" onClick={handleAttachClick} title="Attach strategy document">
                                <PaperclipIcon />
                            </button>
                            <input 
                                type="text" 
                                value={chatInput} 
                                onChange={e => setChatInput(e.target.value)} 
                                placeholder="Type message..." 
                                onKeyDown={e => e.key === 'Enter' && handleSendChatMessage()} 
                            />
                            <button className="chat-send-btn" onClick={handleSendChatMessage}>Send</button>
                        </div>
                    </>
                )}
            </div>
        </div>

        <div className="immersive-app">
            <DottedGlowBackground gap={32} radius={1.5} color="rgba(51, 63, 72, 0.05)" glowColor="#EF6A00" speedScale={0.3} />

            <div className={`stage-container ${focusedArtifactIndex !== null ? 'mode-focus' : 'mode-split'}`}>
                 <div className={`empty-state ${sessions.length > 0 && currentSessionIndex !== -1 || isLoading ? 'fade-out' : ''}`}>
                     <div className="empty-content">
                         <div className="tagline">Brilliantly Boring Since 1865</div>
                         <h1>STRATEGIC <span>FOUNDRY</span></h1>
                         <div className="advisor-tagline">PNC Strategic Foundry Advisor</div>
                         <p>Unique non-obvious insights for the middle market.</p>
                         
                         <div className="recent-sessions">
                             <div className="recent-label">Recent Strategic Inquiries</div>
                             <div className="sessions-list">
                                 {sessions && sessions.length > 0 ? (
                                     sessions.slice().reverse().map((s) => (
                                         <div 
                                             key={s.id} 
                                             className="session-link" 
                                             onClick={() => {
                                                 const idx = sessions.findIndex(found => found.id === s.id);
                                                 setCurrentSessionIndex(idx);
                                                 setFocusedArtifactIndex(null);
                                             }}
                                         >
                                             {s.prompt}
                                         </div>
                                     ))
                                 ) : (
                                     <>
                                         <div className="session-link" onClick={() => handleSendMessage(INITIAL_PLACEHOLDERS[0])}>
                                             {INITIAL_PLACEHOLDERS[0]}
                                         </div>
                                         <div className="session-link" onClick={() => handleSendMessage(INITIAL_PLACEHOLDERS[5])}>
                                             {INITIAL_PLACEHOLDERS[5]}
                                         </div>
                                         <div className="session-link" onClick={() => handleSendMessage(INITIAL_PLACEHOLDERS[1])}>
                                             {INITIAL_PLACEHOLDERS[1]}
                                         </div>
                                     </>
                                 )}
                             </div>
                         </div>
                     </div>
                 </div>

                {/* Navigation arrows for focused artifacts */}
                {focusedArtifactIndex !== null && (
                    <>
                        {focusedArtifactIndex > 0 && (
                            <button 
                                className="nav-cycle-btn left" 
                                onClick={(e) => { e.stopPropagation(); setFocusedArtifactIndex(focusedArtifactIndex - 1); }}
                                title="Previous Strategy Vector"
                            >
                                <ArrowLeftIcon />
                            </button>
                        )}
                        {focusedArtifactIndex < 2 && (
                            <button 
                                className="nav-cycle-btn right" 
                                onClick={(e) => { e.stopPropagation(); setFocusedArtifactIndex(focusedArtifactIndex + 1); }}
                                title="Next Strategy Vector"
                            >
                                <ArrowRightIcon />
                            </button>
                        )}
                    </>
                )}

                {sessions && sessions.map((session, sIndex) => (
                    sIndex === currentSessionIndex && (
                        <div key={session.id} className="session-group active-session" style={{ width: '100%' }}>
                            <div className="artifact-grid">
                                {session.artifacts.map((artifact, aIndex) => (
                                    <ArtifactCard 
                                        key={artifact.id}
                                        artifact={artifact}
                                        isFocused={focusedArtifactIndex === aIndex}
                                        onClick={() => setFocusedArtifactIndex(aIndex)}
                                    />
                                ))}
                            </div>
                        </div>
                    )
                ))}
            </div>

            <div className={`action-bar ${focusedArtifactIndex !== null ? 'visible' : ''}`}>
                <button onClick={() => setFocusedArtifactIndex(null)}><GridIcon /> Return to Overview</button>
            </div>

            <div className="floating-input-container">
                <button 
                  className="pnc-home-button" 
                  onClick={goHome} 
                  title="Return to Foundry Home"
                  style={{ display: (currentSessionIndex === -1 && !isLoading) ? 'none' : 'flex' }}
                >
                  <HomeIcon />
                </button>
                <div className={`input-wrapper ${isLoading ? 'loading' : ''}`}>
                    <input 
                        ref={inputRef} type="text" value={inputValue} 
                        onChange={e => {setInputValue(e.target.value); setIsAutoCycling(false);}} 
                        onKeyDown={handleInputKeyDown} 
                        placeholder={isLoading ? 'Synthesizing...' : placeholders[placeholderIndex]}
                    />
                    <button className="send-button" onClick={() => handleSendMessage()} disabled={isLoading}><ArrowUpIcon /></button>
                </div>
            </div>
        </div>
    </>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root')!);
root.render(<App />);
