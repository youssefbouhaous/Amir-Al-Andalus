<?xml version='1.0' encoding='UTF-8'?>
<tileset version="1.10" tiledversion="1.10.2" name="tileset" tilewidth="32" tileheight="32" tilecount="24" columns="8">
 <image source="../images/tileset.png" width="256" height="96" />
 <tile id="0">
  <properties>
   <property name="name" value="ground" />
  </properties>
 </tile>
 <tile id="1">
  <properties>
   <property name="name" value="dirt" />
  </properties>
 </tile>
 <tile id="2">
  <properties>
   <property name="name" value="stone" />
  </properties>
 </tile>
 <tile id="3">
  <properties>
   <property name="name" value="brick" />
   <property name="spawn" value="brick" />
  </properties>
 </tile>
 <tile id="4">
  <properties>
   <property name="name" value="question" />
   <property name="spawn" value="question" />
   <property name="contents" value="coin" />
  </properties>
 </tile>
 <tile id="5">
  <properties>
   <property name="name" value="question_powerup" />
   <property name="spawn" value="question" />
   <property name="contents" value="powerup" />
  </properties>
 </tile>
 <tile id="6">
  <properties>
   <property name="name" value="question_life" />
   <property name="spawn" value="question" />
   <property name="contents" value="extra_life" />
  </properties>
 </tile>
 <tile id="7">
  <properties>
   <property name="name" value="coin" />
   <property name="spawn" value="coin" />
  </properties>
 </tile>
 <tile id="8">
  <properties>
   <property name="name" value="used_block" />
  </properties>
 </tile>
 <tile id="9">
  <properties>
   <property name="name" value="platform" />
   <property name="collision" value="one_way" />
  </properties>
 </tile>
 <tile id="10">
  <properties>
   <property name="name" value="pipe_top_left" />
  </properties>
 </tile>
 <tile id="11">
  <properties>
   <property name="name" value="pipe_top_right" />
  </properties>
 </tile>
 <tile id="12">
  <properties>
   <property name="name" value="pipe_left" />
  </properties>
 </tile>
 <tile id="13">
  <properties>
   <property name="name" value="pipe_right" />
  </properties>
 </tile>
 <tile id="14">
  <properties>
   <property name="name" value="cloud_left" />
  </properties>
 </tile>
 <tile id="15">
  <properties>
   <property name="name" value="cloud_right" />
  </properties>
 </tile>
 <tile id="16">
  <properties>
   <property name="name" value="bush" />
  </properties>
 </tile>
 <tile id="17">
  <properties>
   <property name="name" value="grass" />
  </properties>
 </tile>
 <tile id="18">
  <properties>
   <property name="name" value="flower" />
  </properties>
 </tile>
 <tile id="19">
  <properties>
   <property name="name" value="fence" />
  </properties>
 </tile>
 <tile id="20">
  <properties>
   <property name="name" value="question_star" />
   <property name="spawn" value="question" />
   <property name="contents" value="star" />
  </properties>
 </tile>
 <tile id="21">
  <properties>
   <property name="name" value="sun_block" />
   <property name="spawn" value="switch_block" />
   <property name="color" value="sun" />
  </properties>
 </tile>
 <tile id="22">
  <properties>
   <property name="name" value="moon_block" />
   <property name="spawn" value="switch_block" />
   <property name="color" value="moon" />
  </properties>
 </tile>
</tileset>