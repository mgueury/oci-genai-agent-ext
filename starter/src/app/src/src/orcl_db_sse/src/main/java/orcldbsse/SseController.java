package orcldbsee;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
public class SseController {
    private final SseIngestService service;

    public SseController(SseIngestService service) {
        this.service = service;
    }

    // Example: POST /startsse?thread_id=abc123
    @PostMapping(path = "/startsse")
    public ResponseEntity<String> startSse(@RequestParam("thread_id") String threadId,
            @RequestBody String jsonBody) {

        service.startAsync(threadId, jsonBody); // fire-and-forget
        return ResponseEntity.accepted().body("SSE ingestion started for thread_id=" + threadId);
    }
}

