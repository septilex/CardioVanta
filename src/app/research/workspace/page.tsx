import Link from "next/link";
import { DocShell } from "../../../components/shell/DocShell";
import { Workspace } from "../../../components/research/Workspace";
import "../../workspace.css";

export const metadata = { title: "Research Workspace | CardioVanta" };

export default function ResearchWorkspace() {
  return <DocShell section="Research workspace"><div className="workspace-page">
    <Link href="/research" className="workspace-link">Back to research</Link>
    <h1>Research workspace</h1>
    <p className="workspace-intro">Manage evaluation metadata and review anonymous explanation feedback. Heart Analysis remains open to everyone.</p>
    <Workspace />
  </div></DocShell>;
}
