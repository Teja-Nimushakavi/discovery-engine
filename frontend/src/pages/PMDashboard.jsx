import { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Loader2, BarChart3, AlertCircle, Database, Sparkles, Send } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function PMDashboard() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResponse, setSearchResponse] = useState(null);
  
  const [analytics, setAnalytics] = useState(null);
  const [isAnalyticsLoading, setIsAnalyticsLoading] = useState(true);

  // 1. Fetch Analytics on Mount
  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await axios.get('http://localhost:8000/api/analytics/summary');
        setAnalytics(res.data);
      } catch (error) {
        console.error('Failed to load analytics', error);
      }
      setIsAnalyticsLoading(false);
    };
    fetchAnalytics();
  }, []);

  // 2. Handle Search Query
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    try {
      // FIX: Added trailing slash to avoid 307 redirect CORS issues
      const res = await axios.post('http://localhost:8000/api/rag/', {
        query,
        namespaces: null
      });
      setSearchResponse(res.data);
    } catch (error) {
      console.error('Failed to run query', error);
      setSearchResponse({ answer: 'Error running query. Please ensure the backend is running.', retrieved_chunks: [] });
    }
    setIsSearching(false);
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: '1200px', margin: '0 auto', paddingBottom: '4rem' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '3rem', textAlign: 'center' }}>
        <h1 className="page-title" style={{ marginBottom: '0.5rem', fontSize: '3rem' }}>Discovery Engine</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1.2rem' }}>Product Intelligence & Photo Retrieval Pain Points</p>
      </div>

      {/* Hero Search Bar */}
      <div className="pm-section animate-fade-in stagger-1">
        <form onSubmit={handleSearch} className="query-box" style={{ padding: '1.5rem 2.5rem' }}>
          <input 
            type="text" 
            className="query-input"
            style={{ fontSize: '1.25rem' }}
            placeholder="Ask anything (e.g. 'What metadata do users forget most when searching?')"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isSearching}
          />
          <button type="submit" className="btn-primary" style={{ padding: '1rem 2rem', fontSize: '1.1rem' }} disabled={isSearching}>
            {isSearching ? <Loader2 className="animate-spin" size={24} /> : <Sparkles size={24} />}
            Synthesize
          </button>
        </form>

        {/* Search Results */}
        {searchResponse && (
          <div className="glass-card animate-fade-in" style={{ borderLeft: '4px solid var(--accent-color)', marginBottom: '3rem' }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', color: 'var(--accent-color)' }}>
              <Send size={20} /> Synthesis Result
            </h3>
            <p style={{ fontSize: '1.15rem', lineHeight: 1.8, color: 'var(--text-primary)' }}>
              {searchResponse.answer}
            </p>
            
            {searchResponse.retrieved_chunks?.length > 0 && (
              <div style={{ marginTop: '2rem', borderTop: '1px solid var(--panel-border)', paddingTop: '1.5rem' }}>
                <h4 style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem', textTransform: 'uppercase' }}>Evidence Sources</h4>
                <div style={{ display: 'grid', gap: '1rem' }}>
                  {searchResponse.retrieved_chunks.map((chunk, idx) => (
                    <div key={idx} style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px' }}>
                       <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        <span className={`badge frustration-${chunk.metadata?.frustration_level || 'low'}`}>
                          {chunk.metadata?.taxonomy_label || 'Unknown'}
                        </span>
                        <span className="badge">{chunk.metadata?.source_platform || 'unknown'}</span>
                      </div>
                      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>"{chunk.metadata?.text}"</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Analytics High Level Overview */}
      <div className="pm-section animate-fade-in stagger-2">
        <h3><BarChart3 size={24} /> Intelligence Overview</h3>
        
        {isAnalyticsLoading ? (
           <div className="glass-card" style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}>
             <Loader2 className="animate-spin" size={32} color="var(--accent-color)" />
           </div>
        ) : !analytics ? (
           <div className="glass-card">Error loading analytics data.</div>
        ) : (
          <>
            <div className="grid-3" style={{ marginBottom: '2rem' }}>
              <div className="glass-card" style={{ textAlign: 'center' }}>
                <div className="metric-title">Total User Feedback</div>
                <div className="metric-value">{analytics.total_chunks}</div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>Vectors processed</p>
              </div>
              <div className="glass-card" style={{ textAlign: 'center' }}>
                <div className="metric-title">Primary Frustration</div>
                <div className="metric-value" style={{ color: 'var(--danger-color)', WebkitTextFillColor: 'initial' }}>High</div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>Retrieval failures drive highest angst</p>
              </div>
              <div className="glass-card" style={{ textAlign: 'center' }}>
                <div className="metric-title">Data Sources</div>
                <div className="metric-value" style={{ color: 'var(--success-color)', WebkitTextFillColor: 'initial' }}>5</div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>App Store, Play, Reddit, etc.</p>
              </div>
            </div>

            <div className="grid-2">
              <div className="glass-card">
                <h3 className="metric-title">Pain Point Taxonomy</h3>
                <div style={{ height: 300, marginTop: '1rem' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={analytics.taxonomy}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                        stroke="none"
                      >
                        {analytics.taxonomy.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: '8px' }}
                        itemStyle={{ color: '#fff' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="glass-card">
                <h3 className="metric-title">User Frustration Severity</h3>
                <div style={{ height: 300, marginTop: '1rem' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.frustration}>
                      <XAxis dataKey="name" stroke="#a0a0a0" />
                      <YAxis stroke="#a0a0a0" />
                      <Tooltip 
                        cursor={{fill: 'rgba(255,255,255,0.05)'}}
                        contentStyle={{ backgroundColor: '#111', border: '1px solid #333', borderRadius: '8px' }}
                      />
                      <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Strategic Insights */}
      <div className="pm-section animate-fade-in stagger-3">
        <h3><AlertCircle size={24} /> Top PM Insights</h3>
        <div className="grid-2">
          <div className="insight-card">
            <h4>1. Visual Memory vs Lexical Search</h4>
            <p>Users vividly remember the color of a dress or the layout of a room, but current search systems rely on exact tags or timeframes, causing total retrieval failure for subjective attributes.</p>
          </div>
          <div className="insight-card">
            <h4>2. The "Loss of Time" Effect</h4>
            <p>The number one forgotten metadata is the exact year/month an event took place. Relying on a timeline scrub as a fallback is failing users with libraries > 10,000 photos.</p>
          </div>
          <div className="insight-card">
            <h4>3. Sequential Search Fatigue</h4>
            <p>When the first search term fails, users rapidly downgrade their queries (e.g. from "dog at beach" to "dog" to scrolling endlessly) before abandoning the platform in frustration.</p>
          </div>
          <div className="insight-card">
            <h4>4. Emotion-based Queries</h4>
            <p>A growing trend is users searching for "vibes" or emotions (e.g. "happy times", "silly"). Current NLP models fail to map these abstract concepts to image context.</p>
          </div>
        </div>
      </div>
      
    </div>
  );
}
