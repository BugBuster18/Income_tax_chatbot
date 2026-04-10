import React, { useState, useRef, useEffect } from 'react';
import { Send, Landmark, Calculator, User } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './index.css';

interface Message {
  role: 'user' | 'system';
  content: string;
}

interface ApiState {
  userQuery: string;
  currentQuery: string;
  contexts: string[] | null;
  originalFullQuestion: string | null;
  preamble: string | null;
  currentQuestion: string | null;
  questionQueue: string[];
  compiledAnswers: { q: string; a: string }[];
}

const PIPELINE_STEPS = [
  { id: 'rewrite', label: 'Query Rewriter' },
  { id: 'rag', label: 'Vector Retrieval' },
  { id: 'json', label: 'Schema Extraction' },
  { id: 'z3', label: 'Z3 Rule Engine' },
  { id: 'final', label: 'Final Output' }
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'system',
      content: 'Hello. I am the Income Tax Assistant. How can I help you today?',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isFollowupLoading, setIsFollowupLoading] = useState(false);
  const [isFollowupMode, setIsFollowupMode] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [apiState, setApiState] = useState<ApiState>({
    userQuery: '',
    currentQuery: '',
    contexts: null,
    originalFullQuestion: null,
    preamble: null,
    currentQuestion: null,
    questionQueue: [],
    compiledAnswers: [],
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, apiState.currentQuestion]);

  // Handle pipeline visualizer progress realistically
  useEffect(() => {
    let timeouts: ReturnType<typeof setTimeout>[] = [];
    if (isLoading) {
       if (apiState.contexts === null) {
         // Initial Run: Start from beginning
         setLoadingStep(0); // 1. Query Rewriter
         timeouts.push(setTimeout(() => setLoadingStep(1), 500));  // 2. Vector Retrieval
         timeouts.push(setTimeout(() => setLoadingStep(2), 1100)); // 3. Schema Extraction (LLM starts)
         
         // LLM takes about 2-3 seconds to extract JSON. 
         // If it needs follow up (reprompt), it returns right after this!
         // So we PAUSE the animation here at step 2 for a full 3.5 seconds.
         // If the backend hasn't returned yet, it means validation passed and we reached the final generation!
         timeouts.push(setTimeout(() => setLoadingStep(3), 4600)); // 4. Rule Engine
         timeouts.push(setTimeout(() => setLoadingStep(4), 5000)); // 5. Final Output
       } else {
         // Reprompt Run: contexts already exist, jumping straight to re-evaluating the new data
         setLoadingStep(2); // Jump back to Schema Extraction
         timeouts.push(setTimeout(() => setLoadingStep(3), 1500)); // Rule Engine (fast)
         timeouts.push(setTimeout(() => setLoadingStep(4), 1900)); // Final Output (LLM final text generation)
       }
    }
    return () => timeouts.forEach(clearTimeout);
  }, [isLoading, apiState.contexts]);

  // Handle autosizing the textarea smoothly
  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to let scrollHeight recalculate properly
      textareaRef.current.style.height = '24px';
      const scrollHeight = textareaRef.current.scrollHeight;
      textareaRef.current.style.height = `${Math.min(scrollHeight, 200)}px`;
    }
  }, [input]);

  const parseOptions = (question: string): string[] => {
    const lowerQ = question.toLowerCase();
    
    // Smart heuristic matching for common tax-related questions
    if (lowerQ.includes('old regime') && lowerQ.includes('new regime')) {
      return ['Old', 'New', 'Both (Compare)'];
    }
    if (lowerQ.includes('metro') || lowerQ.includes('non-metro')) {
      return ['Metro', 'Non-Metro'];
    }
    if (lowerQ.includes(' yes ') || lowerQ.includes(' no ') || lowerQ.startsWith('do you') || lowerQ.startsWith('are you')) {
      // Return yes/no for obvious boolean formats unless it's a "what" question
      if (!lowerQ.startsWith('what') && !lowerQ.startsWith('how')) {
         return ['Yes', 'No'];
      }
    }

    // Fallback: looking for bracketed options like (Option1 / Option2)
    const match = question.match(/\([^)]*\b(yes|no|\/|,|old|new|\d+)\b[^)]*\)/i);
    if (!match) {
        const genericMatch = question.match(/\(([^)]+)\)/);
        if (!genericMatch) return [];
        const rawOptions = genericMatch[1].split(/[\/,]/).map(s => s.trim());
        const cleanOpts = rawOptions.filter(Boolean);
        if (cleanOpts.length >= 2) return cleanOpts;
        return [];
    }
    const parenthesizedContent = match[0].replace(/[()]/g, '');
    const options = parenthesizedContent.split(/[\/,]/).map(s => s.trim()).filter(Boolean);
    return options.length >= 2 ? options : [];
  };

  const cleanQuestion = (question: string): string => {
    // Keep it entirely clean, strip brackets if they appear at the end
    return question.replace(/\([^)]+\)\s*$/g, '').trim();
  };

  const parseMultiPartQuestion = (rawText: string) => {
    // Look for ordered lists like "1. ", "2. "
    const parts = rawText.split(/(?=(?:\n\s*)?\d+\.\s+)/);
    
    if (parts.length > 1) {
      const preamble = parts[0].trim();
      const questions = parts.slice(1)
        .map(q => q.replace(/^(?:\n\s*)?\d+\.\s*/, '').trim())
        .filter(Boolean); // Filter out empty lines that could soft-lock the queue logic
      return { preamble: preamble || null, questions };
    }
    
    // Look for unordered lists like "- ", "* "
    const bulletParts = rawText.split(/(?=(?:\n\s*)?(?:-|\*)\s+)/);
    if (bulletParts.length > 1) {
      const preamble = bulletParts[0].trim();
      const questions = bulletParts.slice(1)
        .map(q => q.replace(/^(?:\n\s*)?(?:-|\*)\s*/, '').trim())
        .filter(Boolean);
      return { preamble: preamble || null, questions };
    }
  
    // Fallback single question
    return { preamble: null, questions: [rawText.trim()].filter(Boolean) };
  };

  const executeBackendFetch = async (uQuery: string, cQuery: string, ctxs: string[] | null) => {
    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_query: uQuery,
          current_query: cQuery,
          contexts: ctxs,
        }),
      });

      if (!res.ok) throw new Error('Network error');
      const data = await res.json();

      if (data.status === 'need_more_info') {
        const { preamble, questions } = parseMultiPartQuestion(data.question);

        if (preamble) {
          setMessages((prev) => [...prev, { role: 'system', content: preamble }]);
        }

        setApiState({
          userQuery: uQuery,
          currentQuery: data.current_query || cQuery,
          contexts: data.contexts || ctxs,
          originalFullQuestion: data.question,
          preamble: preamble,
          currentQuestion: questions[0] || data.question,
          questionQueue: questions.slice(1),
          compiledAnswers: [],
        });
      } else if (data.status === 'success') {
        setMessages((prev) => [...prev, { role: 'system', content: data.final_answer }]);
        setApiState({
          userQuery: '',
          currentQuery: '',
          contexts: null,
          originalFullQuestion: null,
          preamble: null,
          currentQuestion: null,
          questionQueue: [],
          compiledAnswers: [],
        });
        setIsFollowupMode(true); // Engages context-aware lightweight chat instead of heavy pipeline
      } else if (data.status === 'irrelevant' || data.message) {
        setMessages((prev) => [...prev, { role: 'system', content: data.message || 'Irrelevant query.' }]);
        setApiState({
          userQuery: '',
          currentQuery: '',
          contexts: null,
          originalFullQuestion: null,
          preamble: null,
          currentQuestion: null,
          questionQueue: [],
          compiledAnswers: [],
        });
      }
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { role: 'system', content: 'Connection error. Is the backend running?' }]);
      setApiState(prev => ({ ...prev, currentQuestion: null }));
    } finally {
      setIsLoading(false);
    }
  };

  const executeFollowup = async (query: string) => {
    try {
      setIsFollowupLoading(true);
      const res = await fetch('http://localhost:8000/chat/followup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: messages, // Send history
          new_query: query,
        }),
      });
      if (!res.ok) throw new Error('Network error');
      const data = await res.json();
      setMessages((prev) => [...prev, { role: 'system', content: data.reply }]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { role: 'system', content: 'Connection error during follow-up.' }]);
    } finally {
      setIsFollowupLoading(false);
    }
  };

  const handleSend = async (forcedText?: string) => {
    const textToSend = forcedText !== undefined ? forcedText : input;
    if (!textToSend.trim()) return;
    setInput('');
    setSelectedOptions([]); // Clear any multi-select state when moving forward

    // If we're answering a questionnaire pop-up part
    if (apiState.currentQuestion) {
      const newAnswers = [...apiState.compiledAnswers, { q: apiState.currentQuestion, a: textToSend.trim() }];
      
      // Removed setMessages code here as per user request to not log Qs/As into chat

      if (apiState.questionQueue.length > 0) {
        // More questions left in the queue
        const nextQ = apiState.questionQueue[0];
        setApiState((prev) => ({
          ...prev,
          currentQuestion: nextQ,
          questionQueue: prev.questionQueue.slice(1),
          compiledAnswers: newAnswers,
        }));
        return; // Don't call backend yet!
      } else {
        // Queue finished! Compile and send
        setIsLoading(true);
        let compiledClarification = newAnswers.map((pair, idx) => `${idx + 1}. ${pair.a}`).join('\n');
        let payloadCurrentQuery = `${apiState.currentQuery}\nSystem asked: ${apiState.originalFullQuestion}\nUser clarified:\n${compiledClarification}`;

        // Create the unified Q&A compilation block in the chat timeline mimicking the screenshot
        const visualBlock = newAnswers.map((pair) => `**Q:** ${cleanQuestion(pair.q)}\n\n**A:** ${pair.a}`).join('\n\n');
        setMessages((prev) => [...prev, { role: 'user', content: visualBlock }]);

        // Clear popup UI immediately
        setApiState((prev) => ({
          ...prev,
          currentQuestion: null,
          compiledAnswers: [],
        }));

        await executeBackendFetch(apiState.userQuery, payloadCurrentQuery, apiState.contexts);
        return;
      }
    }

    // Normal first-time prompt logic OR Follow-up
    setMessages((prev) => [...prev, { role: 'user', content: textToSend.trim() }]);
    
    // Check if we are in lightweight follow-up mode
    if (isFollowupMode) {
      await executeFollowup(textToSend.trim());
      return;
    }

    setIsLoading(true);

    let payloadUserQuery = apiState.userQuery || textToSend.trim();
    let payloadCurrentQuery = apiState.userQuery ? apiState.currentQuery : textToSend.trim();

    await executeBackendFetch(payloadUserQuery, payloadCurrentQuery, apiState.contexts);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app-container">
      <div className="header">
        <Landmark size={20} style={{ marginRight: '0.5rem', color: 'var(--tax-accent)' }} />
        <h1>Income Tax Assistant</h1>
      </div>
      
      <div className="chat-container">
        {messages.map((msg, i) => (
          <div key={i} className={`message-wrapper ${msg.role}`}>
            {msg.role === 'system' && (
              <div style={{ paddingRight: '1rem', paddingTop: '0.25rem', color: 'var(--tax-accent)' }}>
                <Calculator size={20} />
              </div>
            )}
            <div className={`message ${msg.role}`}>
              <div className="markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>
            </div>
            {msg.role === 'user' && (
              <div style={{ paddingLeft: '1rem', paddingTop: '0.25rem', color: 'var(--text-secondary)' }}>
                <User size={20} />
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="message-wrapper system">
            <div style={{ paddingRight: '1rem', paddingTop: '0.25rem', color: 'var(--tax-accent)' }}>
                <Calculator size={20} />
            </div>
            <div className="message system" style={{ width: '100%', maxWidth: '100%' }}>
              <div className="pipeline-wrapper">
                <div className="pipeline-visualizer">
                  {PIPELINE_STEPS.map((step, idx) => {
                    let status = 'pending';
                    if (idx < loadingStep) status = 'completed';
                    else if (idx === loadingStep) status = 'active';

                    // If we have contexts cached, we are mid-conversation, skipping retrieval steps
                    const isSkipped = apiState.contexts !== null && idx < 2;
                    if (isSkipped) status = 'completed';

                    return (
                      <React.Fragment key={step.id}>
                        <div className={`pipeline-box ${status}`}>
                          {step.label}
                        </div>
                        {idx < PIPELINE_STEPS.length - 1 && (
                          <div className={`pipeline-connector ${status === 'completed' || isSkipped ? 'completed' : ''}`} />
                        )}
                      </React.Fragment>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
        {isFollowupLoading && (
          <div className="message-wrapper system">
            <div style={{ paddingRight: '1rem', paddingTop: '0.25rem', color: 'var(--tax-accent)' }}>
                <Calculator size={20} />
            </div>
            <div className="message system">
              <div className="typing-indicator">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="bottom-wrapper">
        {apiState.currentQuestion && (
          <div className="questionnaire-popup" style={{ animation: 'slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)' }}>
            <div className="questionnaire-topbar">
              <div className="questionnaire-title">
                {cleanQuestion(apiState.currentQuestion)}
              </div>
              <div className="questionnaire-progress">
                <span className="questionnaire-progress-text">
                  &lt; {apiState.compiledAnswers.length + 1} of {apiState.compiledAnswers.length + apiState.questionQueue.length + 1} &gt;
                </span>
                <span className="questionnaire-close" onClick={() => setApiState(prev => ({...prev, currentQuestion: null}))}>
                  {/* Simplistic X icon, matching the image */}
                  ✕
                </span>
              </div>
            </div>
            
            <div className="questionnaire-options-list">
              {(() => {
                // Auto-detect if question warrants multiple selections
                const currentOptions = parseOptions(apiState.currentQuestion || '');
                const qText = (apiState.currentQuestion || '').toLowerCase();
                
                // Heuristic: explicit multi-select keywords or broad listing categories like deductions
                const isMultiSelect = 
                  qText.includes('select all') || 
                  qText.includes('all that apply') || 
                  qText.includes('multiple') || 
                  qText.includes('any of the') || 
                  qText.includes('deduction') ||
                  qText.includes('what kind');

                // Hard override for known strictly-binary single-choice domains
                const isBinary = currentOptions.length <= 2 && (qText.includes('yes') || qText.includes('metro') || qText.includes('do you') || qText.includes('are you'));
                const finalMultiSelect = isMultiSelect && !isBinary;

                return (
                  <>
                    {currentOptions.map((opt, idx) => {
                      const isSelected = selectedOptions.includes(opt);
                      return (
                        <div 
                          key={opt} 
                          onClick={() => {
                            if (finalMultiSelect) {
                              // Multi-select toggle
                              setSelectedOptions(prev => 
                                prev.includes(opt) ? prev.filter(o => o !== opt) : [...prev, opt]
                              );
                            } else {
                              // Single-choice auto-advance
                              handleSend(opt);
                            }
                          }} 
                          className={`option-row ${isSelected ? 'selected' : ''}`}
                          style={isSelected ? { backgroundColor: 'rgba(23, 179, 112, 0.15)', borderColor: 'var(--tax-accent)' } : {}}
                        >
                          <div className="option-number-box" style={isSelected ? { backgroundColor: 'var(--tax-accent)', color: '#fff' } : {}}>{idx + 1}</div>
                          <div className="option-text" style={isSelected ? { color: 'var(--tax-accent)', fontWeight: 500 } : {}}>{opt}</div>
                          <div className="option-arrow" style={isSelected ? { opacity: 1, color: 'var(--tax-accent)' } : {}}>
                            {isSelected ? '✓' : '→'}
                          </div>
                        </div>
                      );
                    })}
                    
                    {finalMultiSelect && selectedOptions.length > 0 && (
                      <div 
                        className="option-row" 
                        onClick={() => handleSend(selectedOptions.join(', '))}
                        style={{ 
                          justifyContent: 'center', 
                          backgroundColor: 'var(--tax-accent)', 
                          color: 'white', 
                          marginTop: '0.75rem',
                          border: 'none',
                          padding: '0.9rem'
                        }}
                      >
                        <div className="option-text" style={{ textAlign: 'center', fontWeight: 600, color: 'white' }}>
                          Confirm Selection ({selectedOptions.length})
                        </div>
                      </div>
                    )}
                  </>
                );
              })()}
              
              {/* Always provide a "Something else" pencil row that prompts them to just type below */}
              <div className="option-row custom-row" onClick={() => textareaRef.current?.focus()}>
                <div className="option-number-box">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>
                  </svg>
                </div>
                <div className="option-text" style={{ color: '#909090'}}>
                  {parseOptions(apiState.currentQuestion).length > 0 ? 'Something else (type below)' : 'Type your answer below...'}
                </div>
                {/* Visual gap filler */}
              </div>
            </div>
          </div>
        )}

        <div className="input-container">
          <div className="input-box">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask me anything about income tax..."
              rows={1}
              disabled={isLoading}
              style={{ overflowY: 'hidden' }}
            />
            <button 
              className="send-button"
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
