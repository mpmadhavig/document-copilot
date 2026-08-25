export function ChatIndexPage() {
  return (
    <div className="research-canvas flex h-full items-center justify-center overflow-y-auto px-6 py-10">
      <div className="w-full max-w-2xl text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-cyan-400 via-violet-500 to-indigo-700 text-sm font-black text-white shadow-2xl shadow-violet-300/40">DC</div>
        <p className="mt-6 text-xs font-semibold uppercase tracking-[0.2em] text-violet-700">Research workspace</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-slate-950 sm:text-5xl">
          Turn filings into<br />verifiable answers.
        </h1>
        <p className="mx-auto mt-5 max-w-xl leading-7 text-slate-600">
          Create a research thread from the sidebar, ask a focused question, and inspect every source before using the answer downstream.
        </p>
        <div className="mt-9 grid gap-3 text-left sm:grid-cols-3">
          <FeatureCard number="01" title="Ask" text="Use a company, year, form, or disclosure to focus retrieval." />
          <FeatureCard number="02" title="Compare" text="Trace how language and reported figures change over time." />
          <FeatureCard number="03" title="Verify" text="Open every citation beside the answer in one click." />
        </div>
      </div>
    </div>
  )
}

function FeatureCard({
  number,
  title,
  text,
}: {
  number: string
  title: string
  text: string
}) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-sm backdrop-blur">
      <span className="text-[10px] font-bold tracking-[0.16em] text-violet-500">{number}</span>
      <p className="mt-2 font-semibold text-slate-950">{title}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{text}</p>
    </div>
  )
}
