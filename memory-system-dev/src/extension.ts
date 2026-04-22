import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand('memorySystemDev.setupMCP', async () => {
        // Path to the packaged executable
        const exeName = process.platform === 'win32' ? 'memory_mcp_server.exe' : 'memory_mcp_server';
        const exePath = path.join(context.extensionPath, 'bin', exeName);
        
        if (!fs.existsSync(exePath)) {
            vscode.window.showErrorMessage(`Executable not found at ${exePath}. Was it packaged correctly?`);
            return;
        }

        // Determine paths for common MCP clients
        let baseStoragePath = '';
        if (process.platform === 'win32') {
            baseStoragePath = path.join(os.homedir(), 'AppData', 'Roaming', 'Code', 'User', 'globalStorage');
        } else if (process.platform === 'darwin') {
            baseStoragePath = path.join(os.homedir(), 'Library', 'Application Support', 'Code', 'User', 'globalStorage');
        } else {
            baseStoragePath = path.join(os.homedir(), '.config', 'Code', 'User', 'globalStorage');
        }

        const targets = [
            {
                name: 'Roo Code',
                configPath: path.join(baseStoragePath, 'rooveterinaryinc.roo-cline', 'settings', 'cline_mcp.json')
            },
            {
                name: 'Cline',
                configPath: path.join(baseStoragePath, 'saoudrizwan.claude-dev', 'settings', 'cline_mcp.json')
            }
        ];

        let injectedCount = 0;

        for (const target of targets) {
            if (fs.existsSync(target.configPath)) {
                try {
                    const content = fs.readFileSync(target.configPath, 'utf8');
                    const json = JSON.parse(content);
                    
                    if (!json.mcpServers) {
                        json.mcpServers = {};
                    }
                    
                    json.mcpServers['memory-system'] = {
                        command: exePath,
                        args: [],
                        env: {
                            MEMORY_WORKSPACE_ROOT: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || ''
                        }
                    };
                    
                    fs.writeFileSync(target.configPath, JSON.stringify(json, null, 2), 'utf8');
                    injectedCount++;
                    vscode.window.showInformationMessage(`Successfully configured memory-system MCP for ${target.name}!`);
                } catch (err: any) {
                    vscode.window.showErrorMessage(`Failed to modify config for ${target.name}: ${err.message}`);
                }
            }
        }

        if (injectedCount === 0) {
            // Also suggest user configures it manually via clipboard
            vscode.env.clipboard.writeText(JSON.stringify({
                "memory-system": {
                    command: exePath,
                    args: []
                }
            }, null, 2));
            vscode.window.showWarningMessage('No known MCP clients found to auto-inject. Copied configuration to clipboard for manual setup.');
        }
    });

    context.subscriptions.push(disposable);
    
    // Auto-prompt on activation
    vscode.window.showInformationMessage('Memory System Dev MCP is ready.', 'Setup Now').then(val => {
        if (val === 'Setup Now') {
            vscode.commands.executeCommand('memorySystemDev.setupMCP');
        }
    });
}

export function deactivate() {}
