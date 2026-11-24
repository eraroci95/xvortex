export default function ComingSoon({ title, phase, children }: { title: string; phase: number; children: string }) {
  return (
    <section>
      <h1 className="text-2xl font-semibold">{title}</h1>
      <div className="glass mt-6 max-w-xl rounded-2xl p-6">
        <p>{children}</p>
        <p className="mt-3 text-sm text-dim">
          This module is built in phase {phase}. Nothing on this screen is sample data.
        </p>
      </div>
    </section>
  );
}
