'use client';

import { useEffect, useRef, useState } from 'react';
import { BookOpenCheck, Check, ChevronDown, ExternalLink, FileText, Files, Layers3, LoaderCircle, LogOut, MessageSquare, MessagesSquare, Plus, Send, ShieldCheck, Sparkles, Ticket, Upload, UserRound, Workflow, X, Eye, EyeOff, ArrowRight, ChartNoAxesCombined, CircleHelp } from 'lucide-react';

type Role = 'employee' | 'admin';
type Session = { role: Role; is_demo: boolean; csrf_token: string; expires: number };
type Config = { demo_enabled: boolean; normal_login_enabled: boolean; generation_enabled: boolean; retrieval: string; version: string; remember_days: number };
type Source = { id: string; document_id: string; title: string; section: string; text: string; updated: number; role: Role };
type Answer = { id: string; status: 'answered' | 'withheld'; answer: string; sources: Source[]; mode: 'generated' | 'extractive'; reason: string; retrieval?: string };
type Message = { question: string; result: Answer };
type Manual = { id: string; title: string; text: string; role: Role; updated: number; seeded: boolean };
type Issue = { id: string; question: string; answer: string; sources: Source[]; status: 'open' | 'in_progress' | 'closed'; created: number };
type Usage = { model: string; status: string; input_tokens: number; output_tokens: number; cost: number | null; created: number };
type Overview = { usage: Usage[]; audit: { event: string; role: string; is_demo: boolean; created: number }[]; model: string | null; daily_limit: number; session_limit: number; embedding_model: string | null; pricing_configured: boolean };
type Screen = 'chat' | 'docs' | 'tickets' | 'admin' | 'design';

const sampleQuestions = ['VPNにつながらない', 'パスワードを忘れた', 'メールが送信できない', '私物PCで業務をしたい', '管理者のアカウント復旧手順は？'];
const statusLabels = { open: '受付済み', in_progress: '対応中', closed: '解決済み' };
const formatDate = (stamp: number) => new Intl.DateTimeFormat('ja-JP', { dateStyle: 'medium', timeZone: 'Asia/Tokyo' }).format(new Date(stamp * 1000));

function Brand() {
  return <div className="brand"><span className="brand-icon"><Layers3 size={22} /></span><div><strong>Enterprise AI Helpdesk</strong><small>架空企業 · 社内ITサポート</small></div></div>;
}

function Sources({ sources }: { sources: Source[] }) {
  return <div className="sources">{sources.map(source => <details className="source" key={source.id}>
    <summary><FileText size={16} /><span><strong>{source.title}</strong><small>{source.section} · {formatDate(source.updated)} 更新</small></span><ChevronDown size={16} /></summary>
    <div className="source-body"><span className="eyebrow">参照した原文 · 架空資料</span><p>{source.text}</p></div>
  </details>)}</div>;
}

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [booting, setBooting] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [screen, setScreen] = useState<Screen>('chat');
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [manuals, setManuals] = useState<Manual[]>([]);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [editor, setEditor] = useState<{ id?: string; title: string; text: string; role: Role } | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [resolved, setResolved] = useState<string[]>([]);
  const loginForm = useRef<HTMLFormElement>(null);
  const chatBottom = useRef<HTMLDivElement>(null);

  function clearPrivateState() {
    setMessages([]); setManuals([]); setIssues([]); setOverview(null); setEditor(null); setDeleteId(null); setResolved([]); setQuestion(''); setScreen('chat');
  }

  async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers);
    if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    if (session && options.method && options.method !== 'GET') headers.set('X-CSRF-Token', session.csrf_token);
    const response = await fetch(`/api${path}`, { ...options, headers, credentials: 'same-origin', cache: 'no-store' });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      if (response.status === 401 && path !== '/auth/login') { setSession(null); clearPrivateState(); }
      throw new Error(typeof body.detail === 'string' ? body.detail : '入力内容を確認して、もう一度お試しください。');
    }
    return response.json();
  }

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch('/api/config', { cache: 'no-store' }).then(r => { if (!r.ok) throw new Error(); return r.json(); }),
      fetch('/api/auth/me', { cache: 'no-store' }).then(r => r.ok ? r.json() : null),
    ]).then(([settings, identity]) => { if (active) { setConfig(settings); setSession(identity); } })
      .catch(() => { if (active) setError('サーバーに接続できません。少し待って画面を再読み込みしてください。'); })
      .finally(() => { if (active) setBooting(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!session) return;
    let active = true;
    async function load() {
      try {
        if (screen === 'docs') { const data = await api<Manual[]>('/documents'); if (active) setManuals(data); }
        if (screen === 'tickets') { const data = await api<Issue[]>('/tickets'); if (active) setIssues(data); }
        if (screen === 'admin') { const data = await api<Overview>('/admin/overview'); if (active) setOverview(data); }
      } catch (err) { if (active) setError((err as Error).message); }
    }
    void load();
    return () => { active = false; };
    // api reads the current session. Reload only when identity or screen changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screen, session]);

  useEffect(() => { if (messages.length) chatBottom.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, [messages]);

  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setNotice(''); setBusy(true);
    const form = new FormData(event.currentTarget);
    try {
      const identity = await api<Session>('/auth/login', { method: 'POST', body: JSON.stringify({ email: form.get('email'), password: form.get('password'), remember }) });
      loginForm.current?.reset(); clearPrivateState(); setSession(identity);
    } catch (err) { setError((err as Error).message); }
    finally { if (loginForm.current) { const field = loginForm.current.elements.namedItem('password') as HTMLInputElement; if (field) field.value = ''; } setBusy(false); }
  }

  async function demo(role: Role) {
    setBusy(true); setError(''); setNotice('');
    try {
      const identity = await api<Session>('/auth/demo', { method: 'POST', body: JSON.stringify({ role }) });
      loginForm.current?.reset(); clearPrivateState(); setSession(identity);
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function logout() {
    setBusy(true); setError('');
    try { await api('/auth/logout', { method: 'POST' }); setSession(null); clearPrivateState(); setNotice('ログアウトしました。'); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function ask(text: string) {
    const q = text.trim();
    if (busy || q.length < 3) { if (!busy) setError('質問は3文字以上で入力してください。'); return; }
    setBusy(true); setError(''); setNotice('');
    try { const result = await api<Answer>('/chat', { method: 'POST', body: JSON.stringify({ question: q }) }); setMessages(old => [...old, { question: q, result }]); setQuestion(''); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function handoff(id: string) {
    setBusy(true); setError('');
    try { await api('/tickets', { method: 'POST', body: JSON.stringify({ answer_id: id }) }); setScreen('tickets'); setNotice('会話と出典を添えて、問い合わせを登録しました。'); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function saveManual(event: React.FormEvent) {
    event.preventDefault(); if (!editor) return; setBusy(true); setError('');
    try { const { id, ...body } = editor; await api(`/documents${id ? `/${id}` : ''}`, { method: id ? 'PUT' : 'POST', body: JSON.stringify(body) }); setManuals(await api('/documents')); setEditor(null); setNotice('文書を保存しました。次の検索から反映されます。'); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  async function uploadPdf(file: File | undefined) {
    if (!file) return;
    if (file.size > 2_000_000) { setError('PDFは2MB以下にしてください。'); return; }
    setBusy(true); setError('');
    const form = new FormData(); form.append('file', file);
    try { await api('/documents/pdf', { method: 'POST', body: form }); setManuals(await api('/documents')); setNotice('PDFを登録しました。閲覧範囲は「IT管理者のみ」です。編集から変更できます。'); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  const nav = [
    { id: 'chat' as Screen, label: 'AIに相談', icon: MessagesSquare },
    { id: 'docs' as Screen, label: 'ナレッジ', icon: Files },
    { id: 'tickets' as Screen, label: '問い合わせ', icon: Ticket },
    ...(session?.role === 'admin' ? [{ id: 'admin' as Screen, label: '利用状況', icon: ChartNoAxesCombined }] : []),
    { id: 'design' as Screen, label: '設計・評価', icon: Workflow },
  ];

  if (!session) return <div className="login-page">
    <header className="topbar login-topbar"><Brand /><span className="portfolio-label">PORTFOLIO DEMO</span></header>
    <main className="login-grid">
      <section className="login-intro"><div className="eyebrow">YOUR INTERNAL IT PARTNER</div><h1>社内の「困った」に、<br />根拠のある答えを。</h1><p className="intro-copy">社内マニュアルを検索し、出典付きで回答。<br />解決できないときは、IT窓口へつなぎます。</p>
        <div className="benefits">{[
          { Icon: BookOpenCheck, title: '回答の根拠がわかる', text: '参照したマニュアルを、その場で確認。' },
          { Icon: ShieldCheck, title: '権限に応じて情報を表示', text: '社員と管理者、それぞれの利用範囲で。' },
          { Icon: MessagesSquare, title: '解決まで、ひとつの流れで', text: '回答が難しい内容は問い合わせへ引き継ぎ。' },
        ].map(({ Icon, title, text }) => <div className="benefit" key={title}><Icon size={21} /><div><strong>{title}</strong><p>{text}</p></div></div>)}</div>
        <p className="fiction-note">架空企業の社内ITサポートを想定した作品です。<br />実在企業のシステム・資料は使用していません。</p>
      </section>
      <section className="login-card" aria-label="ログイン"><span className="badge">Enterprise AI Helpdesk</span><h2>ログイン</h2><p className="muted">アカウントをお持ちの方</p>
        <form onSubmit={signIn} ref={loginForm}>
          <label className="field">メールアドレス<input type="email" name="email" placeholder="name@example.com" autoComplete="username" maxLength={200} required disabled={busy || booting} /></label>
          <label className="field">パスワード<span className="password-field"><input type={showPassword ? 'text' : 'password'} name="password" placeholder="パスワードを入力" autoComplete="current-password" maxLength={128} required disabled={busy || booting} /><button type="button" className="icon-button" aria-label={showPassword ? 'パスワードを隠す' : 'パスワードを表示'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></span></label>
          <label className="remember"><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} disabled={busy || booting} aria-describedby="remember-note" /><span>ログインしたままにする</span></label><p id="remember-note" className="field-note">30日間保持します。共有の端末ではチェックを外してください。</p>
          <button className="primary login-submit" disabled={busy || booting}>{busy || booting ? <><LoaderCircle size={17} className="spin" />確認中…</> : 'ログイン'}</button>
          <button type="button" className="text-button" onClick={() => { setError(''); setNotice('パスワードの再設定は、このデモの管理者にご連絡ください。セルフサービスのメール再設定は未対応です。'); }}>パスワードをお忘れですか？</button>
        </form>
        {error && <p className="alert error" role="alert">{error}</p>}{notice && <p className="alert info" role="status">{notice}</p>}
        {config?.demo_enabled && <><div className="divider"><span>アカウントなしで試す</span></div><div className="demo-buttons"><button className="secondary demo-button" disabled={busy || booting} onClick={() => demo('employee')}><UserRound size={19} /><span><strong>社員としてデモ体験</strong><small>質問・出典確認・問い合わせ</small></span><ArrowRight size={17} /></button><button className="secondary demo-button" disabled={busy || booting} onClick={() => demo('admin')}><ShieldCheck size={19} /><span><strong>管理者としてデモ体験</strong><small>管理者向け資料と利用状況も確認</small></span><ArrowRight size={17} /></button></div></>}
        <p className="card-note">{config?.normal_login_enabled ? '通常アカウントは管理者が発行します。' : '通常アカウントは未発行です。デモ体験からお試しください。'} デモでは架空データのみを扱います。</p>
      </section>
    </main><footer className="login-footer">Enterprise AI Helpdesk · 架空データによるポートフォリオ</footer>
  </div>;

  return <div className="app-page">
    <header className="topbar"><Brand /><div className="session-controls"><span className="badge">{session.role === 'admin' ? 'IT管理者' : '社員'}{session.is_demo ? 'デモ' : ''}</span><button className="secondary logout" onClick={logout} disabled={busy}><LogOut size={15} />ログアウト</button></div></header>
    {session.is_demo && <div className="demo-banner"><ShieldCheck size={14} /><span>デモモード · 架空データのみ使用 · 共有資料は閲覧専用 · 問い合わせは訪問者ごとに分離されます</span></div>}
    <div className="app-shell"><aside className="sidebar"><nav aria-label="メインメニュー">{nav.map(({ id, label, icon: Icon }) => <button key={id} aria-current={screen === id ? 'page' : undefined} disabled={busy} onClick={() => { setScreen(id); setError(''); setNotice(''); setEditor(null); setDeleteId(null); }}><Icon size={18} />{label}</button>)}</nav><div className="sidebar-note"><span className="eyebrow">PORTFOLIO DEMO</span><p>架空データを使用<br />実在企業とは無関係</p><span className="system-state"><span />{config?.generation_enabled ? 'AI接続設定あり' : '根拠抜粋モード'}</span></div></aside>
      <main className="workspace">
        {error && <div className="alert error" role="alert">{error}<button className="icon-button" aria-label="エラーを閉じる" onClick={() => setError('')}><X size={16} /></button></div>}
        {notice && <div className="alert info" role="status">{notice}<button className="icon-button" aria-label="通知を閉じる" onClick={() => setNotice('')}><X size={16} /></button></div>}

        {screen === 'chat' && <><div className="page-heading"><span className="eyebrow">IT SUPPORT</span><h1>困りごとを、解決へ。</h1><p>社内マニュアルをもとに、根拠のある回答を。</p></div>
          <div className="chat-layout"><section className="chat-panel" aria-label="IT相談"><div className="panel-heading"><h2><MessagesSquare size={18} />AIに相談</h2><span>参照範囲：{session.role === 'admin' ? '全社員・IT管理者' : '全社員'}向け資料</span></div>
            {!messages.length && <div className="chat-welcome"><span className="welcome-icon"><Sparkles size={25} /></span><h2>どのようなことでお困りですか？</h2><p>質問を入力するか、右のサンプルからお試しください。<br />回答の根拠となったマニュアルも確認できます。</p>{!config?.generation_enabled && <span className="mode-note">現在はAI未接続のため、関連資料の本文を抜粋して表示します。</span>}</div>}
            <div className="conversation" aria-live="polite">{messages.map(({ question: q, result }) => <article className="exchange" key={result.id}><div className="user-question"><UserRound size={16} /><p>{q}</p></div><div className="answer-label">{result.status === 'withheld' ? <CircleHelp size={17} /> : result.mode === 'generated' ? <Sparkles size={17} /> : <BookOpenCheck size={17} />}<span>{result.status === 'withheld' ? '回答を保留しました' : result.mode === 'generated' ? 'AIによる回答' : 'マニュアルの根拠抜粋'}</span></div><p className="answer-text">{result.answer}</p><Sources sources={result.sources} /><div className="answer-actions">{result.status === 'answered' && <button className="secondary small-button" onClick={() => setResolved(old => [...old, result.id])} disabled={resolved.includes(result.id)}><Check size={14} />{resolved.includes(result.id) ? '解決済みにしました' : '解決しました'}</button>}<button className="secondary small-button" disabled={busy} onClick={() => handoff(result.id)}><Ticket size={14} />{result.status === 'withheld' ? 'IT窓口へ引き継ぐ' : '解決しないので問い合わせる'}</button></div></article>)}</div>
            {busy && <p className="working" role="status"><LoaderCircle size={16} className="spin" />参照できる資料を確認しています…</p>}
            <form className="composer" onSubmit={event => { event.preventDefault(); void ask(question); }}><label htmlFor="question">質問する</label><div><textarea id="question" value={question} onChange={event => setQuestion(event.target.value)} maxLength={1000} minLength={3} required rows={2} disabled={busy} placeholder="例：VPNにつながりません" /><button className="primary" disabled={busy || question.trim().length < 3}><Send size={16} />送信</button></div><p>パスワード・個人情報・実際の社内情報は入力しないでください。</p></form><div ref={chatBottom} />
          </section><aside className="suggestions"><h2>まずは試してみる</h2>{sampleQuestions.map(q => <button className="sample-question" key={q} onClick={() => ask(q)} disabled={busy}><span>{q}</span><ArrowRight size={14} /></button>)}<div className="suggestion-note"><BookOpenCheck size={18} /><p>出典を押すと、回答のもとになった原文を開けます。</p></div><div className="suggestion-note"><ShieldCheck size={18} /><p>権限の違いを試すには、一度ログアウトして別のデモを選択してください。</p></div></aside></div>
        </>}

        {screen === 'docs' && <><div className="page-heading heading-with-actions"><div><span className="eyebrow">KNOWLEDGE</span><h1>ナレッジ</h1><p>現在の権限で参照できるマニュアルです。</p></div>{session.role === 'admin' && <div className="inline-actions"><label className={`secondary upload-button ${session.is_demo || busy ? 'disabled' : ''}`}><Upload size={16} />PDF登録<input type="file" accept="application/pdf,.pdf" disabled={session.is_demo || busy} onChange={e => { void uploadPdf(e.target.files?.[0]); e.target.value = ''; }} /></label><button className="primary" disabled={session.is_demo || busy} onClick={() => setEditor({ title: '', text: '', role: 'admin' })}><Plus size={16} />文書登録</button></div>}</div>
          {session.is_demo && session.role === 'admin' && <p className="alert info">管理者デモでは共有資料を変更できません。通常の管理者アカウントでは登録・編集・削除を利用できます。</p>}
          {editor && <form className="editor panel" onSubmit={saveManual}><h2>{editor.id ? '文書を編集' : '文書を登録'}</h2><label className="field">タイトル<input value={editor.title} onChange={e => setEditor({ ...editor, title: e.target.value })} required maxLength={100} /></label><label className="field">閲覧範囲<select value={editor.role} onChange={e => setEditor({ ...editor, role: e.target.value as Role })}><option value="admin">IT管理者のみ</option><option value="employee">全社員</option></select></label><label className="field">本文<textarea value={editor.text} onChange={e => setEditor({ ...editor, text: e.target.value })} required minLength={20} maxLength={40000} rows={9} placeholder="# 見出し&#10;手順を入力してください。" /></label><div className="inline-actions"><button className="primary" disabled={busy}>保存</button><button className="secondary" type="button" onClick={() => setEditor(null)} disabled={busy}>キャンセル</button></div></form>}
          <section className="panel manual-list">{manuals.length ? manuals.map(manual => <article key={manual.id} className="manual"><details><summary><FileText size={19} /><span><strong>{manual.title}</strong><small>{manual.role === 'admin' ? 'IT管理者のみ' : '全社員'} · {formatDate(manual.updated)} 更新</small></span><ChevronDown size={16} /></summary><p className="manual-text">{manual.text}</p></details>{session.role === 'admin' && !session.is_demo && <div className="manual-actions"><button className="text-button" disabled={busy} onClick={() => { setEditor(manual); setDeleteId(null); }}>編集</button><button className="text-button danger-text" disabled={busy} onClick={() => setDeleteId(manual.id)}>削除</button></div>}{deleteId === manual.id && <div className="delete-confirm"><p>「{manual.title}」を削除しますか？</p><button className="secondary" disabled={busy} onClick={async () => { setBusy(true); setError(''); try { await api(`/documents/${manual.id}`, { method: 'DELETE' }); setManuals(await api('/documents')); setDeleteId(null); setNotice('文書を削除しました。'); } catch (err) { setError((err as Error).message); } finally { setBusy(false); } }}>削除する</button><button className="secondary" disabled={busy} onClick={() => setDeleteId(null)}>キャンセル</button></div>}</article>) : <p className="muted">文書を読み込んでいます。文書が未登録の場合はここには表示されません。</p>}</section><p className="page-footnote">PDFはテキストを含む2MB・30ページ以下に対応。OCRは未対応です。</p>
        </>}

        {screen === 'tickets' && <><div className="page-heading"><span className="eyebrow">HANDOFF</span><h1>問い合わせ</h1><p>{session.is_demo ? 'このデモセッションで引き継いだ問い合わせです。' : session.role === 'admin' ? '通常アカウントから届いた問い合わせを管理します。' : 'あなたが登録した問い合わせを確認できます。'}</p></div><section className="panel ticket-list">{issues.length ? issues.map(issue => <article className="issue" key={issue.id}><div className="issue-header"><span className="ticket-id">HD-{issue.id.slice(0, 8).toUpperCase()}</span><span className={`status status-${issue.status}`}>{statusLabels[issue.status]}</span></div><h2>{issue.question}</h2><p className="muted small">{formatDate(issue.created)} 登録 · 回答と出典を添付</p><details className="ticket-detail"><summary>引き継いだ内容を確認<ChevronDown size={15} /></summary><p className="answer-text">{issue.answer}</p><Sources sources={issue.sources} /></details>{session.role === 'admin' && <label className="ticket-status-label">対応状況<select value={issue.status} disabled={busy} onChange={async e => { setBusy(true); setError(''); try { await api(`/tickets/${issue.id}`, { method: 'PATCH', body: JSON.stringify({ status: e.target.value }) }); setIssues(await api('/tickets')); } catch (err) { setError((err as Error).message); } finally { setBusy(false); } }}>{Object.entries(statusLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>}</article>) : <div className="empty-state"><Ticket size={30} /><h2>問い合わせはまだありません</h2><p>AIの回答画面から、会話と出典を添えて引き継げます。</p><button className="secondary" onClick={() => setScreen('chat')}>AIに相談する</button></div>}</section><p className="page-footnote">{session.is_demo ? '実際のIT窓口への送信はありません。デモの問い合わせはログアウト時に削除されます。' : 'このアプリ内で管理します。外部チケットシステムやメールへの通知は未接続です。'}</p></>}

        {screen === 'admin' && session.role === 'admin' && <><div className="page-heading"><span className="eyebrow">OPERATIONS</span><h1>利用状況</h1><p>{session.is_demo ? 'このデモセッションのAI利用を確認できます。他の訪問者の情報は表示しません。' : 'AIの利用量と操作の記録を確認できます。'}</p></div>{overview ? <><section className="panel"><h2>モデル接続と利用上限</h2><dl className="settings-list"><div><dt>回答生成</dt><dd>{overview.model || '未接続 · 根拠抜粋モード'}</dd></div><div><dt>検索</dt><dd>{overview.embedding_model ? `文字bigram TF-IDF + ${overview.embedding_model}で再順位付け` : '文字bigram TF-IDF（キーワードベース）'}</dd></div><div><dt>AI利用上限</dt><dd>全体 {overview.daily_limit} 問 / UTC日 · 1セッション {overview.session_limit} 問</dd></div><div><dt>概算費用</dt><dd>{overview.pricing_configured ? '設定した単価から算出（生成のみ・税別）' : '単価未設定のため表示しません'}</dd></div></dl><p className="page-footnote">モデル・APIキー・上限の変更はサーバーの環境変数で行います。画面からの追加・切替は未実装です。</p></section><section className="panel usage-panel"><h2>AIリクエスト履歴</h2>{overview.usage.length ? <div className="table-wrap"><table><thead><tr><th>モデル</th><th>結果</th><th>入力 / 出力トークン</th><th>概算 USD</th></tr></thead><tbody>{overview.usage.map((item, i) => <tr key={i}><td>{item.model}</td><td>{item.status === 'success' ? '成功' : item.status === 'error' ? '接続・検証失敗' : '処理中'}</td><td>{item.input_tokens} / {item.output_tokens}</td><td>{item.cost === null ? '未設定' : item.cost.toFixed(6)}</td></tr>)}</tbody></table></div> : <p className="muted">AIへのリクエストはまだありません。根拠抜粋モードでは外部AIを呼び出しません。</p>}</section>{!session.is_demo && <section className="panel usage-panel"><h2>監査ログ</h2><p className="muted small">質問本文・パスワード・トークンは記録しません。</p><div className="audit-list">{overview.audit.map((item, i) => <div key={i}><code>{item.event}</code><span>{item.role || '未認証'}{item.is_demo ? ' · デモ' : ''}</span><small>{formatDate(item.created)}</small></div>)}</div></section>}</> : <p role="status">利用状況を読み込んでいます…</p>}</>}

        {screen === 'design' && <><div className="page-heading"><span className="eyebrow">BEHIND THE APP</span><h1>設計・評価</h1><p>この作品で実装したことと、現在の制約を説明します。</p></div><section className="panel design-panel"><h2>回答までの流れ</h2><ol className="flow-list">{['サーバー側でログインと権限を確認', '権限内の文書だけを検索候補にする', '文字bigram TF-IDFで関連箇所を検索', 'AI接続時は資料を渡し、出典IDを検証', '出典付き回答、または回答保留', '解決しない場合は会話ごと問い合わせへ'].map((item, i) => <li key={item}><span>{String(i + 1).padStart(2, '0')}</span>{item}</li>)}</ol></section><section className="panel design-panel"><h2>技術構成</h2><dl className="settings-list"><div><dt>画面</dt><dd>Next.js / React / TypeScript · 静的エクスポート</dd></div><div><dt>API</dt><dd>Python / FastAPI</dd></div><div><dt>データ</dt><dd>SQLite · セッション / 文書 / 問い合わせ / 監査ログ</dd></div><div><dt>AI接続</dt><dd>LiteLLM ProxyのOpenAI互換API（任意接続）</dd></div></dl></section><section className="panel design-panel"><h2>認証とデモの分離</h2><p>パスワードはscryptでハッシュ化し、セッションIDのハッシュをDBに保存します。ブラウザーにはHttpOnly Cookieを渡し、操作時にはCSRFトークンを確認します。</p><p>通常ログインは最大12時間。「ログインしたままにする」を選ぶと30日間です。デモ体験は2時間で、共有文書の変更は許可しません。</p><p>問い合わせへの引き継ぎに必要な会話本文は保存します。監査ログは操作の種類のみ記録し、デモ会話はログアウトまたは24時間経過後の定期的な整理時に削除します。</p></section><section className="panel design-panel"><h2>現在の制約</h2><p>無料公開用のSQLiteは、ホスティング先の再起動でリセットされる構成です。実業務用の永続データベースではありません。</p><p>未接続時の回答はAI生成ではなく、検索した資料の抜粋です。キーワード検索には言い換えへの弱さがあり、根拠の判定と生成回答の正しさには継続的な評価が必要です。</p><p>PDFのOCR、セルフサービスのパスワード再設定、画面からのモデル切替、外部チケット連携は未対応です。</p><p className="small muted">テスト結果と再現手順はリポジトリのREADME・docsに記録します。実在企業での改善効果を示すものではありません。</p></section></>}
      </main>
    </div>
  </div>;
}
