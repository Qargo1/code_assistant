package core.bridges.java.SecureTerminal;
public class SecureShell {
    private static final String[] ALLOWED_COMMANDS = {"ls", "pwd", "git"};
    private static final long MAX_RUN_TIME = 5000; // 5 seconds
    
    public static String execute(String command) throws SecurityException {
        if(!isAllowed(command)) {
            throw new SecurityException("Command not allowed");
        }

        ProcessBuilder pb = new ProcessBuilder("bash", "-c", command)
            .redirectErrorStream(true)
            .directory(Paths.get("/safe_dir").toFile());

        try {
            Process p = pb.start();
            if(!p.waitFor(MAX_RUN_TIME, TimeUnit.MILLISECONDS)) {
                p.destroy();
                throw new TimeoutException("Command timed out");
            }
            
            return new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        } catch (Exception e) {
            throw new RuntimeException("Execution failed: " + e.getMessage());
        }
    }

    private static boolean isAllowed(String cmd) {
        return Arrays.stream(ALLOWED_COMMANDS).anyMatch(cmd::startsWith);
    }
}