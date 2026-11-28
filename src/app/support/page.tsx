import Link from "next/link";
import { DocShell } from "../../components/shell/DocShell";
import { Support } from "../../components/research/Support";
import "../workspace.css";

export const metadata = { title: "Support the Project | CardioVanta" };
export default function SupportPage() {
  return <DocShell section="Project support"><div className="workspace-page">
    <Link href="/research" className="workspace-link">Back to research</Link>
    <h1>Support the learning behind CardioVanta</h1>
    <p className="workspace-intro">Explore a test checkout for voluntary project support. Heart Analysis is free to access, and support is never connected to an assessment or medical service.</p>
    <Support />
  </div></DocShell>;
}
