import Link from "next/link";
export default function NotFound() {
  return <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-[#080c19] p-8 text-slate-100">
    <h1 className="text-4xl font-semibold">Page not found</h1>
    <p className="text-slate-300">This OrbitMinder page does not exist.</p>
    <Link href="/" className="rounded-xl bg-cyan-300 px-5 py-3 font-semibold text-slate-950">Back to home</Link>
  </main>;
}
