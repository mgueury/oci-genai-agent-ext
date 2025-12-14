package orcldbsse;

import com.example.dto.StartSseRequest;
import com.example.service.SseIngestService;
import io.micronaut.http.HttpResponse;
import io.micronaut.http.MediaType;
import io.micronaut.http.annotation.*;

import jakarta.inject.Inject;

@Controller
public class StartSseController { 

  @Inject
  SseIngestService sseIngestService; 

  @Post(uri = "/startsse", consumes = MediaType.APPLICATION_JSON)
  public HttpResponse<String> start(@Body StartSseRequest body) {
    sseIngestService.startAndIngest(body);
    return HttpResponse.accepted("SSE started");
  }
}