// Tailcat carries only two bounded signaling operations, never arbitrary HTTP or keys.
package main

import (
    "bufio"
    "bytes"
    "context"
    "encoding/json"
    "flag"
    "fmt"
    "io"
    "net"
    "net/http"
    "net/url"
    "os"
    "time"

    "github.com/tailscale/tailcat"
)

type request struct { Op string `json:"op"`; Data json.RawMessage `json:"data"` }

func main() {
    target := flag.String("target", "", "Loopback signaling origin")
    flag.Parse()
    parsed, err := url.Parse(*target)
    if err != nil || parsed.Scheme != "http" || parsed.Hostname() != "127.0.0.1" || parsed.Path != "" || parsed.RawQuery != "" || parsed.User != nil {
        fmt.Fprintln(os.Stderr, "Loopback target required"); os.Exit(1)
    }
    secret := os.Getenv("TAILKEY_SIGNAL_TOKEN")
    if len(secret) < 32 { fmt.Fprintln(os.Stderr, "Signal token required"); os.Exit(1) }
    server := &tailcat.Server{Logf: func(string, ...any) {}}
    ctx, cancel := context.WithTimeout(context.Background(), 45*time.Second)
    defer cancel()
    listener, err := server.Listen(ctx, "tcp", ":1")
    if err != nil { fmt.Fprintln(os.Stderr, "Tailcat bootstrap unavailable"); os.Exit(1) }
    defer server.Close()
    json.NewEncoder(os.Stdout).Encode(map[string]string{"addr": string(server.TailcatAddr())})
    // Closing the parent's stdin also terminates the embedded helper.
    go func() { io.Copy(io.Discard, os.Stdin); listener.Close(); server.Close() }()
    slots := make(chan struct{}, 4)
    client := &http.Client{Timeout: 35*time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
    for {
        conn, err := listener.Accept()
        if err != nil { return }
        select {
        case slots <- struct{}{}:
            go func(c net.Conn) { defer func(){ <-slots }(); serve(c, client, *target, secret) }(conn)
        default: conn.Close()
        }
    }
}

func serve(conn net.Conn, client *http.Client, target, secret string) {
    defer conn.Close()
    conn.SetDeadline(time.Now().Add(90*time.Second))
    scan := bufio.NewScanner(conn)
    scan.Buffer(make([]byte, 4096), 70000)
    for count := 0; count < 2 && scan.Scan(); count++ {
        var incoming request
        if json.Unmarshal(scan.Bytes(), &incoming) != nil || (incoming.Op != "ice" && incoming.Op != "offer") || len(incoming.Data) > 65536 { return }
        req, err := http.NewRequest("POST", target+"/api/"+incoming.Op, bytes.NewReader(incoming.Data))
        if err != nil { return }
        req.Header.Set("Content-Type", "application/json")
        req.Header.Set("Origin", target)
        req.Header.Set("X-Tailcat-Token", secret)
        resp, err := client.Do(req)
        if err != nil { return }
        body, err := io.ReadAll(io.LimitReader(resp.Body, 65537))
        resp.Body.Close()
        if err != nil || len(body) > 65536 { return }
        var data any
        if resp.StatusCode == 200 && json.Unmarshal(body, &data) != nil { return }
        if json.NewEncoder(conn).Encode(map[string]any{"status": resp.StatusCode, "data": data}) != nil { return }
    }
}
