// Real Local agent fixture: no network model calls and one disposable file tool.
const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

exports.activate = async function (context) {
  const root = vscode.workspace.workspaceFolders[0].uri.fsPath;
  const log = value => fs.appendFileSync(
    path.join(root, 'report.jsonl'), JSON.stringify(value) + '\n'
  );
  let calls = 0, cfg = {}, busy = false, last = null;

  context.subscriptions.push(vscode.lm.registerTool('humanwill_test_marker', {
    invoke: async options => {
      fs.writeFileSync(path.join(root, 'marker'), 'synthetic');
      log({ case: cfg.case, tool: 'executed', input: options.input });
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart('Synthetic done')
      ]);
    }
  }));
  context.subscriptions.push(vscode.lm.registerLanguageModelChatProvider('humanwill-fixture', {
    provideLanguageModelChatInformation: async () => [{
      id: 'synthetic', name: 'Synthetic fixture', family: 'synthetic', version: '1',
      maxInputTokens: 100000, maxOutputTokens: 1000, capabilities: { toolCalling: true }
    }],
    provideTokenCount: async () => 1,
    provideLanguageModelChatResponse: async (model, messages, options, progress) => {
      calls++;
      log({ case: cfg.case, modelCall: calls, tools: (options.tools || []).map(t => t.name) });
      if (calls === 1) {
        const tool = (options.tools || []).find(t => t.name.includes('humanwill_test_marker'));
        if (!tool) throw Error('No fixture tool');
        progress.report(new vscode.LanguageModelToolCallPart(
          'fixture-call', tool.name, { value: cfg.toolValue }
        ));
      } else {
        progress.report(new vscode.LanguageModelTextPart('Synthetic fixture complete.'));
      }
    }
  }));

  const cp = vscode.extensions.getExtension('GitHub.copilot-chat');
  log({
    vscode: vscode.version, copilot: cp?.packageJSON.version,
    trusted: vscode.workspace.isTrusted, ready: true
  });
  if (cp) cp.activate().catch(e => log({ activationError: String(e) }));

  async function tick() {
    if (busy) return;
    try {
      const next = JSON.parse(fs.readFileSync(path.join(root, 'fixture.json'), 'utf8'));
      if (next.case === last) return;
      if (!next.case) return;
      busy = true;
      last = next.case;
      cfg = next;
      calls = 0;
      fs.rmSync(path.join(root, 'marker'), { force: true });
      log({ case: cfg.case, started: true });
      await vscode.commands.executeCommand('workbench.action.chat.newChat');
      const result = await vscode.commands.executeCommand('workbench.action.chat.open', {
        query: cfg.prompt, blockOnResponse: true, mode: 'agent',
        modelSelector: { vendor: 'humanwill-fixture', id: 'synthetic' },
        toolsInclude: ['humanwill_test_marker']
      });
      await new Promise(r => setTimeout(r, 1000));
      // Do not retain the host's full result (rendered context and session details).
      log({
        case: cfg.case, done: true, agent: result?.metadata?.agentId,
        calls, marker: fs.existsSync(path.join(root, 'marker'))
      });
    } catch (e) {
      log({ case: cfg.case, error: String(e) });
    } finally {
      busy = false;
    }
  }
  const timer = setInterval(tick, 1000);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });
};
