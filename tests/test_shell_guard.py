"""ExecTool 安全检查测试.

验证 _guard_command 方法对危险命令和正常命令的判断。
"""

import pytest

from finchbot.tools.shell import ExecTool


class TestExecToolGuard:
    """ExecTool 安全检查测试类."""

    @pytest.fixture
    def tool(self) -> ExecTool:
        """创建 ExecTool 实例."""
        return ExecTool()

    def test_curl_wttr_in_allowed(self, tool: ExecTool) -> None:
        """测试 wttr.in curl 命令应该被允许."""
        commands = [
            'curl -s "wttr.in/北京?format=3"',
            'curl -s "wttr.in/北京?format=%l:+%c+%t+%h+%w"',
            'curl -s "wttr.in/北京?T"',
            'curl -s "https://wttr.in/Shanghai?format=3"',
        ]
        for cmd in commands:
            result = tool._guard_command(cmd, "/tmp")
            assert result is None, f"命令应该被允许: {cmd}"

    def test_open_meteo_allowed(self, tool: ExecTool) -> None:
        """测试 Open-Meteo API curl 命令应该被允许."""
        cmd = 'curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"'
        result = tool._guard_command(cmd, "/tmp")
        assert result is None, "Open-Meteo API 命令应该被允许"

    def test_format_disk_blocked(self, tool: ExecTool) -> None:
        """测试磁盘格式化命令应该被阻止."""
        dangerous_commands = [
            "format C:\\",
            "format c:",
            "format /dev/sda",
            "format /dev/nvme0n1",
        ]
        for cmd in dangerous_commands:
            result = tool._guard_command(cmd, "/tmp")
            assert result is not None, f"危险命令应该被阻止: {cmd}"
            assert "安全检查阻止" in result

    def test_mkfs_blocked(self, tool: ExecTool) -> None:
        """测试 mkfs 命令应该被阻止."""
        commands = [
            "mkfs.ext4 /dev/sda1",
            "mkfs -t ext4 /dev/sda1",
        ]
        for cmd in commands:
            result = tool._guard_command(cmd, "/tmp")
            assert result is not None, f"mkfs 命令应该被阻止: {cmd}"

    def test_diskpart_blocked(self, tool: ExecTool) -> None:
        """测试 diskpart 命令应该被阻止."""
        cmd = "diskpart"
        result = tool._guard_command(cmd, "/tmp")
        assert result is not None, "diskpart 命令应该被阻止"

    def test_rm_rf_blocked(self, tool: ExecTool) -> None:
        """测试 rm -rf 命令应该被阻止."""
        commands = [
            "rm -rf /",
            "rm -rf /*",
            "rm -fr /home",
        ]
        for cmd in commands:
            result = tool._guard_command(cmd, "/tmp")
            assert result is not None, f"rm -rf 命令应该被阻止: {cmd}"

    def test_shutdown_blocked(self, tool: ExecTool) -> None:
        """测试关机命令应该被阻止."""
        commands = [
            "shutdown now",
            "reboot",
            "poweroff",
        ]
        for cmd in commands:
            result = tool._guard_command(cmd, "/tmp")
            assert result is not None, f"关机命令应该被阻止: {cmd}"

    def test_normal_commands_allowed(self, tool: ExecTool) -> None:
        """测试正常命令应该被允许."""
        commands = [
            "ls -la",
            "echo 'hello'",
            "cat /etc/hosts",
            "python --version",
            "git status",
            "npm install",
            "curl -s https://example.com",
        ]
        for cmd in commands:
            result = tool._guard_command(cmd, "/tmp")
            assert result is None, f"正常命令应该被允许: {cmd}"

    def test_url_format_parameter_allowed(self, tool: ExecTool) -> None:
        """测试 URL 中的 format 参数不应该触发误报."""
        commands = [
            'curl "http://example.com/api?format=json"',
            'curl "http://example.com/api?format=xml&version=1"',
            'wget "http://example.com/download?format=zip"',
        ]
        for cmd in commands:
            result = tool._guard_command(cmd, "/tmp")
            assert result is None, f"URL format 参数不应该触发误报: {cmd}"

    def test_allow_patterns_whitelist(self) -> None:
        """测试 allow_patterns 白名单功能."""
        tool = ExecTool(allow_patterns=[r"wttr\.in", r"open-meteo\.com"])

        assert tool._guard_command('curl -s "http://wttr.in/Beijing"', "/tmp") is None
        assert tool._guard_command('curl -s "https://api.open-meteo.com/v1/forecast"', "/tmp") is None

    def test_allow_patterns_bypass_deny(self) -> None:
        """测试 allow_patterns 可以绕过 deny_patterns."""
        tool = ExecTool(allow_patterns=[r"safe-format\.com"])

        result = tool._guard_command('curl "http://safe-format.com/api?format=json"', "/tmp")
        assert result is None, "allow_patterns 应该绕过 deny_patterns"

    def test_empty_allow_patterns(self, tool: ExecTool) -> None:
        """测试空 allow_patterns 不影响正常检查."""
        assert tool.allow_patterns == []
        assert tool._guard_command("ls -la", "/tmp") is None
        assert tool._guard_command("format C:", "/tmp") is not None
