package orcldbsse;

import io.micronaut.core.annotation.Introspected;

@Introspected
public class StartSseRequest {
  private String session_id;
  private String user_id;
  private String question; 

  public String getSession_id() { return session_id; }
  public void setSession_id(String session_id) { this.session_id = session_id; } 

  public String getUser_id() { return user_id; }
  public void setUser_id(String user_id) { this.user_id = user_id; } 

  public String getQuestion() { return question; }
  public void setQuestion(String question) { this.question = question; }
}